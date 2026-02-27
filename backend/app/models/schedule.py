# DEPRECATED: Schedule model has been removed.
# Schedules and Terms were merged into a single Terms table.
# Assignments now belong directly to Terms via term_id foreign key.
#
# Historical reference:
# - Schedules table had 1:1 relationship with Terms (via term_id UNIQUE)
# - This violated YAGNI principle - unnecessary complexity
# - Merged into Terms table in Phase 1 refactor
#
# Migration date: 2025-02-11
# See: docker/init.sql for current schema
