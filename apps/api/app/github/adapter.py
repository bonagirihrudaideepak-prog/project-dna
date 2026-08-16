"""GitHub repository data adapter.

Fetches repository artifacts through the GitHub REST API. Repository text is
treated as untrusted data: we never execute anything and we minimize retention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

USER_AGENT = "project-dna/1.0"


class GitHubError(Exception):
    def __init__(self, message: str, code: str = "GITHUB_ERROR", retryable: bool = False):
        self.message = message
        self.code = code
        self.retryable = retryable
        super().__init__(message)


class GitHubRateLimited(GitHubError):
    def __init__(self, retry_after: str | None = None):
        super().__init__("GitHub data retrieval is temporarily rate-limited.", "GITHUB_RATE_LIMITED", True)
        self.retry_after = retry_after


@dataclass
class GitHubArtifact:
    type: str  # release | pr | issue | commit | tag
    provider_id: str
    title: str | None
    occurred_at: str | None
    source_url: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


class GitHubAdapter:
    def __init__(self, token: str | None = None, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get(self, url: str, params: dict | None = None) -> Any:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        client = self._client or httpx.AsyncClient(headers=headers, timeout=30.0)
        self._client = client
        resp = await client.get(self.base_url + url, params=params)
        if resp.status_code == 403:
            raise GitHubRateLimited(str(resp.headers.get("x-ratelimit-reset")))
        if resp.status_code == 404:
            raise GitHubError("Repository not found or not accessible.", "REPO_NOT_FOUND")
        if resp.status_code == 401:
            raise GitHubError("GitHub authentication failed.", "GITHUB_UNAUTHORIZED")
        if resp.status_code >= 400:
            raise GitHubError(f"GitHub request failed: {resp.status_code}", "GITHUB_REQUEST_FAILED", True)
        return resp.json()

    async def _paginate(self, url: str, params: dict | None = None, limit: int = 100) -> list[Any]:
        results: list[Any] = []
        page_params = dict(params or {})
        page = 1
        per_page = 100
        while len(results) < limit:
            page_params["page"] = page
            page_params["per_page"] = per_page
            batch = await self._get(url, page_params)
            if not batch:
                break
            results.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
        return results[:limit]

    async def repository(self, full_name: str) -> dict[str, Any]:
        data = await self._get(f"/repos/{full_name}")
        return {
            "github_repo_id": data["id"],
            "full_name": data["full_name"],
            "owner": data["owner"]["login"],
            "name": data["name"],
            "visibility": data.get("visibility", "public"),
            "default_branch": data.get("default_branch", "main"),
            "description": data.get("description"),
        }

    async def default_branch_sha(self, full_name: str, branch: str) -> str:
        data = await self._get(f"/repos/{full_name}/branches/{branch}")
        return data["commit"]["sha"]

    async def list_repositories(self, q: str = "", page: int = 1, per_page: int = 30) -> dict[str, Any]:
        if q:
            data = await self._get("/search/repositories", {"q": q, "page": page, "per_page": per_page})
            return {"items": data.get("items", []), "total_count": data.get("total_count", 0)}
        data = await self._get(f"/user/repos", {"page": page, "per_page": per_page, "visibility": "public"})
        return {"items": data, "total_count": len(data)}

    async def releases(self, full_name: str, limit: int = 100) -> list[GitHubArtifact]:
        data = await self._paginate(f"/repos/{full_name}/releases", limit=limit)
        out = []
        for r in data:
            if r.get("draft"):
                continue
            out.append(
                GitHubArtifact(
                    type="release",
                    provider_id=f"github:release:{r['id']}",
                    title=r.get("name") or r.get("tag_name"),
                    occurred_at=r.get("published_at") or r.get("created_at"),
                    source_url=r.get("html_url"),
                    metadata={"tag": r.get("tag_name"), "body": (r.get("body") or "")[:2000]},
                )
            )
        return out

    async def tags(self, full_name: str, limit: int = 100) -> list[GitHubArtifact]:
        data = await self._paginate(f"/repos/{full_name}/tags", limit=limit)
        return [
            GitHubArtifact(
                type="tag",
                provider_id=f"github:tag:{t['name']}",
                title=f"Tag {t['name']}",
                occurred_at=None,
                source_url=t.get("commit", {}).get("html_url"),
                metadata={"name": t["name"], "sha": t["commit"]["sha"]},
            )
            for t in data
        ]

    async def commits(self, full_name: str, branch: str, limit: int = 2000) -> list[GitHubArtifact]:
        data = await self._paginate(
            f"/repos/{full_name}/commits", {"sha": branch}, limit=limit
        )
        out = []
        for c in data:
            commit = c.get("commit", {})
            author = commit.get("author") or {}
            out.append(
                GitHubArtifact(
                    type="commit",
                    provider_id=f"github:commit:{c['sha']}",
                    title=(commit.get("message") or "").split("\n")[0],
                    occurred_at=author.get("date"),
                    source_url=c.get("html_url"),
                    metadata={
                        "sha": c["sha"],
                        "author_login": (c.get("author") or {}).get("login"),
                        "author_name": (author.get("name")) or None,
                        "message": (commit.get("message") or "")[:3000],
                        "parents": [p["sha"] for p in c.get("parents", [])],
                    },
                )
            )
        return out

    async def pull_requests(self, full_name: str, state: str = "all", limit: int = 500) -> list[GitHubArtifact]:
        data = await self._paginate(
            f"/repos/{full_name}/pulls", {"state": state, "sort": "updated"}, limit=limit
        )
        out = []
        for p in data:
            merged_at = p.get("merged_at")
            out.append(
                GitHubArtifact(
                    type="pr",
                    provider_id=f"github:pr:{p['number']}",
                    title=p.get("title"),
                    occurred_at=merged_at or p.get("closed_at") or p.get("created_at"),
                    source_url=p.get("html_url"),
                    metadata={
                        "number": p["number"],
                        "state": p.get("state"),
                        "merged_at": merged_at,
                        "body": (p.get("body") or "")[:3000],
                        "labels": [l["name"] for l in p.get("labels", [])],
                        "author_login": (p.get("user") or {}).get("login"),
                    },
                )
            )
        return out

    async def issues(self, full_name: str, state: str = "all", limit: int = 500) -> list[GitHubArtifact]:
        data = await self._paginate(
            f"/repos/{full_name}/issues", {"state": state}, limit=limit
        )
        out = []
        for i in data:
            if "pull_request" in i:
                continue
            out.append(
                GitHubArtifact(
                    type="issue",
                    provider_id=f"github:issue:{i['number']}",
                    title=i.get("title"),
                    occurred_at=i.get("created_at"),
                    source_url=i.get("html_url"),
                    metadata={
                        "number": i["number"],
                        "state": i.get("state"),
                        "labels": [l["name"] for l in i.get("labels", [])],
                        "body": (i.get("body") or "")[:3000],
                        "author_login": (i.get("user") or {}).get("login"),
                    },
                )
            )
        return out

    async def contributors(self, full_name: str, limit: int = 100) -> list[dict]:
        data = await self._paginate(f"/repos/{full_name}/contributors", limit=limit)
        return [
            {"login": c.get("login"), "contributions": c.get("contributions"), "avatar_url": c.get("avatar_url")}
            for c in data
        ]

    async def languages(self, full_name: str) -> dict[str, int]:
        return await self._get(f"/repos/{full_name}/languages")

    async def archive_bytes(self, full_name: str, sha: str) -> bytes:
        headers = {"User-Agent": USER_AGENT}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        client = self._client or httpx.AsyncClient(timeout=120.0)
        self._client = client
        resp = await client.get(
            f"https://codeload.github.com/{full_name}/zip/{sha}", headers=headers
        )
        if resp.status_code == 403:
            raise GitHubRateLimited()
        if resp.status_code != 200:
            raise GitHubError(f"Archive download failed: {resp.status_code}", "ARCHIVE_DOWNLOAD_FAILED", True)
        return resp.content

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
