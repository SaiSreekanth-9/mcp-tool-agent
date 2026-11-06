# On-Call Runbook

When the API returns 500 errors, first check the status page and the recent
deploy log. If a deploy just went out, roll it back. If the outage affects
the search endpoint, enable the read-only fallback so customers can still
browse. Page the on-call engineer and post an update to the status page
within 15 minutes. Never restart the database without a second engineer
confirming the plan.
