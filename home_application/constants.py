# -*- coding: utf-8 -*-
import os


def _int_env(name, default):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# JOB execution settings. Override these in PaaS/module env vars after creating
# your own JOB plans.
JOB_BK_BIZ_ID = _int_env("JOB_BK_BIZ_ID", 3)
SEARCH_FILE_PLAN_ID = _int_env("SEARCH_FILE_PLAN_ID", 1001658)
BACKUP_FILE_PLAN_ID = _int_env("BACKUP_FILE_PLAN_ID", 1001659)

MAX_ATTEMPTS = _int_env("JOB_MAX_ATTEMPTS", 10)
JOB_RESULT_ATTEMPTS_INTERVAL = float(os.getenv("JOB_RESULT_ATTEMPTS_INTERVAL", "0.2"))

BK_JOB_HOST = (
    os.getenv("BKPAAS_JOB_URL")
    or os.getenv("BK_JOB_HOST")
    or "https://job.ce.bktencent.com"
)

WAITING_CODE = 2
SUCCESS_CODE = 3
WEB_SUCCESS_CODE = 0
