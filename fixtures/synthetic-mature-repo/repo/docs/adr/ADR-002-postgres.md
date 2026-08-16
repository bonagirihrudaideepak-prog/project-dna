# PostgreSQL adapter

The repository was migrated from MongoDB to PostgreSQL in June 2026.

## Context

The project introduced relationships among users, wardrobes, outfits, and feedback.

## Decision

Use PostgreSQL for the first deployment.

## Alternatives

1. Keep MongoDB and add application-side joins
2. Move to PostgreSQL
3. Use SQLite for the first deployment

## Outcome

Query code became shorter in the measured feature path; deployment setup became more complex.