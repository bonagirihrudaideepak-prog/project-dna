# Wardrobe API

A wardrobe management API. Users can create wardrobes, outfits, and share feedback.

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
uvicorn src.main:app
```

## Configuration

Set `DATABASE_URL`, `GITHUB_CLIENT_ID`, and `SECRET_KEY` in `.env`.

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

## License

MIT