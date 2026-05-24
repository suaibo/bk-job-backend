# -*- coding: utf-8 -*-
import json
import os
import time

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

from blueapps.account.decorators import login_exempt
from blueking.component.shortcuts import get_client_by_request, get_client_by_user
from home_application.constants import (
    BACKUP_FILE_PLAN_ID,
    BK_JOB_HOST,
    JOB_BK_BIZ_ID,
    JOB_RESULT_ATTEMPTS_INTERVAL,
    MAX_ATTEMPTS,
    SEARCH_FILE_PLAN_ID,
    SUCCESS_CODE,
    WAITING_CODE,
    WEB_SUCCESS_CODE,
)
from home_application.models import BackupRecord, BizInfo


api_login_exempt = login_exempt if settings.DEBUG else lambda func: func


def home(request):
    return render(request, "home_application/index_home.html")


def dev_guide(request):
    return render(request, "home_application/dev_guide.html")


def contact(request):
    return render(request, "home_application/contact.html")


def _param_as_int(request, name):
    value = request.GET.get(name)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _missing_param_response(name):
    return JsonResponse({
        "result": False,
        "message": "missing required parameter: {}".format(name),
        "data": {"count": 0, "info": []},
    }, status=400)


def _get_component_client(request):
    bk_token = request.COOKIES.get("bk_token")
    if bk_token:
        return get_client_by_request(request, bk_token=bk_token)
    if settings.DEBUG:
        return get_client_by_user(os.getenv("BK_DEV_USERNAME", "admin"))
    return get_client_by_request(request)


def _get_request_username(request):
    user = getattr(request, "user", None)
    username = getattr(user, "username", None)
    return username or os.getenv("BK_DEV_USERNAME", "admin")


def _json_response(result=True, data=None, message="success"):
    return JsonResponse({
        "result": result,
        "code": WEB_SUCCESS_CODE,
        "message": message,
        "data": data,
    })


def _parse_host_id_list(request):
    raw_value = request.GET.get("host_id_list")
    if not raw_value:
        return None, _missing_param_response("host_id_list")

    try:
        host_id_list = [
            int(item.strip())
            for item in raw_value.split(",")
            if item.strip()
        ]
    except (TypeError, ValueError):
        return None, JsonResponse({
            "result": False,
            "code": WEB_SUCCESS_CODE,
            "message": "invalid parameter: host_id_list",
            "data": [],
        }, status=400)

    if not host_id_list:
        return None, _missing_param_response("host_id_list")
    return host_id_list, None


def _required_query(request, name):
    value = request.GET.get(name)
    if value in (None, ""):
        return None, _missing_param_response(name)
    return value, None


def _execute_job_plan_and_wait(client, plan_id, global_var_list, fail_message):
    execute_result = client.jobv3.execute_job_plan(
        bk_scope_type="biz",
        bk_scope_id=JOB_BK_BIZ_ID,
        job_plan_id=plan_id,
        global_var_list=global_var_list,
    )
    if not execute_result.get("result"):
        return None, None, _json_response(False, None, execute_result.get("message", fail_message))

    job_instance_id = (execute_result.get("data") or {}).get("job_instance_id")
    if not job_instance_id:
        return None, None, _json_response(False, None, fail_message)

    status_kwargs = {
        "bk_scope_type": "biz",
        "bk_scope_id": JOB_BK_BIZ_ID,
        "job_instance_id": job_instance_id,
    }
    step_instance_list = []
    for _ in range(MAX_ATTEMPTS):
        status_result = client.jobv3.get_job_instance_status(**status_kwargs)
        if not status_result.get("result"):
            return None, None, _json_response(False, None, status_result.get("message", fail_message))

        step_instance_list = (status_result.get("data") or {}).get("step_instance_list") or []
        if not step_instance_list:
            time.sleep(JOB_RESULT_ATTEMPTS_INTERVAL)
            continue

        status = step_instance_list[0].get("status")
        if status == WAITING_CODE:
            time.sleep(JOB_RESULT_ATTEMPTS_INTERVAL)
            continue
        if status == SUCCESS_CODE:
            return job_instance_id, step_instance_list[0].get("step_instance_id"), None
        return None, None, _json_response(False, None, fail_message)

    return None, None, _json_response(False, None, "{}: timeout".format(fail_message))


def _load_job_log(client, job_instance_id, step_instance_id, bk_host_id):
    response = client.jobv3.get_job_instance_ip_log(
        bk_scope_type="biz",
        bk_scope_id=JOB_BK_BIZ_ID,
        job_instance_id=job_instance_id,
        step_instance_id=step_instance_id,
        bk_host_id=bk_host_id,
    )
    if not response.get("result"):
        return {
            "bk_host_id": bk_host_id,
            "message": response.get("message", "get job log failed"),
        }

    data = response.get("data") or {}
    log_content = data.get("log_content") or "{}"
    try:
        log_data = json.loads(log_content)
    except (TypeError, ValueError):
        return {
            "bk_host_id": bk_host_id,
            "message": log_content or "empty job log",
        }

    if isinstance(log_data, dict):
        log_data["bk_host_id"] = data.get("bk_host_id") or bk_host_id
    return log_data


def _job_result_link(job_instance_id):
    return "{}/biz/{}/execute/task/{}".format(
        BK_JOB_HOST.rstrip("/"),
        JOB_BK_BIZ_ID,
        job_instance_id,
    )


@api_login_exempt
def get_bizs_list(request):
    """Fetch the business list from local cache first, then CMDB."""
    bizs = BizInfo.objects.all().order_by("bk_biz_id")
    if bizs.exists():
        return JsonResponse({
            "result": True,
            "message": "success",
            "data": {
                "count": bizs.count(),
                "info": list(bizs.values("bk_biz_id", "bk_biz_name")),
            },
        })

    client = _get_component_client(request)
    result = client.cc.search_business({
        "fields": ["bk_biz_id", "bk_biz_name"],
        "page": {
            "start": 0,
            "limit": 100,
            "sort": "",
        },
    })

    if result.get("result") and result.get("data"):
        for biz in result["data"].get("info", []):
            BizInfo.objects.update_or_create(
                bk_biz_id=biz["bk_biz_id"],
                defaults={"bk_biz_name": biz["bk_biz_name"]},
            )
    return JsonResponse(result)


@api_login_exempt
def get_sets_list(request):
    """Fetch set list by business id."""
    bk_biz_id = _param_as_int(request, "bk_biz_id")
    if bk_biz_id is None:
        return _missing_param_response("bk_biz_id")

    client = _get_component_client(request)
    result = client.cc.search_set({
        "bk_biz_id": bk_biz_id,
        "fields": [
            "bk_set_id",
            "bk_set_name",
            "bk_biz_id",
            "bk_created_at",
            "bk_supplier_account",
        ],
    })
    return JsonResponse(result)


@api_login_exempt
def get_modules_list(request):
    """Fetch module list by business id and set id."""
    bk_biz_id = _param_as_int(request, "bk_biz_id")
    bk_set_id = _param_as_int(request, "bk_set_id")
    if bk_biz_id is None:
        return _missing_param_response("bk_biz_id")
    if bk_set_id is None:
        return _missing_param_response("bk_set_id")

    client = _get_component_client(request)
    result = client.cc.search_module({
        "bk_biz_id": bk_biz_id,
        "bk_set_id": bk_set_id,
        "fields": [
            "bk_module_id",
            "bk_module_name",
            "bk_set_id",
            "bk_biz_id",
            "bk_created_at",
            "bk_supplier_account",
        ],
    })
    return JsonResponse(result)


@api_login_exempt
def get_hosts_list(request):
    """Fetch host list by business id and optional set/module/operator filters."""
    bk_biz_id = _param_as_int(request, "bk_biz_id")
    if bk_biz_id is None:
        return _missing_param_response("bk_biz_id")

    kwargs = {
        "bk_biz_id": bk_biz_id,
        "page": {
            "start": 0,
            "limit": 100,
        },
        "fields": [
            "bk_host_id",
            "bk_host_innerip",
            "operator",
            "bk_bak_operator",
        ],
    }

    bk_set_id = _param_as_int(request, "bk_set_id")
    if bk_set_id is not None:
        kwargs["bk_set_ids"] = [bk_set_id]

    bk_module_id = _param_as_int(request, "bk_module_id")
    if bk_module_id is not None:
        kwargs["bk_module_ids"] = [bk_module_id]

    operator = request.GET.get("operator")
    if operator:
        kwargs["host_property_filter"] = {
            "condition": "AND",
            "rules": [{
                "field": "operator",
                "operator": "contains",
                "value": operator,
            }],
        }

    client = _get_component_client(request)
    result = client.cc.list_biz_hosts(kwargs)
    return JsonResponse(result)


@api_login_exempt
def get_host_detail(request):
    """Fetch host detail by host id."""
    bk_host_id = _param_as_int(request, "bk_host_id")
    if bk_host_id is None:
        return _missing_param_response("bk_host_id")

    client = _get_component_client(request)
    result = client.cc.get_host_base_info({"bk_host_id": bk_host_id})
    return JsonResponse(result)


@api_login_exempt
def search_file(request):
    """Search files on selected hosts through a JOB execution plan."""
    host_id_list, error_response = _parse_host_id_list(request)
    if error_response:
        return error_response

    search_path, error_response = _required_query(request, "search_path")
    if error_response:
        return error_response

    suffix, error_response = _required_query(request, "suffix")
    if error_response:
        return error_response

    client = _get_component_client(request)
    job_instance_id, step_instance_id, error_response = _execute_job_plan_and_wait(
        client,
        SEARCH_FILE_PLAN_ID,
        [
            {
                "name": "host_list",
                "server": {"host_id_list": host_id_list},
            },
            {
                "name": "search_path",
                "value": search_path,
            },
            {
                "name": "suffix",
                "value": suffix,
            },
        ],
        "search failed",
    )
    if error_response:
        return error_response

    log_list = [
        _load_job_log(client, job_instance_id, step_instance_id, bk_host_id)
        for bk_host_id in host_id_list
    ]
    return _json_response(True, log_list)


@api_login_exempt
def backup_file(request):
    """Backup matched files on selected hosts through a JOB execution plan."""
    host_id_list, error_response = _parse_host_id_list(request)
    if error_response:
        return error_response

    search_path, error_response = _required_query(request, "search_path")
    if error_response:
        return error_response

    suffix, error_response = _required_query(request, "suffix")
    if error_response:
        return error_response

    backup_path, error_response = _required_query(request, "backup_path")
    if error_response:
        return error_response

    client = _get_component_client(request)
    job_instance_id, step_instance_id, error_response = _execute_job_plan_and_wait(
        client,
        BACKUP_FILE_PLAN_ID,
        [
            {
                "name": "host_list",
                "server": {"host_id_list": host_id_list},
            },
            {
                "name": "search_path",
                "value": search_path,
            },
            {
                "name": "suffix",
                "value": suffix,
            },
            {
                "name": "backup_path",
                "value": backup_path,
            },
        ],
        "backup failed",
    )
    if error_response:
        return error_response

    username = _get_request_username(request)
    job_link = _job_result_link(job_instance_id)
    created_records = []
    for bk_host_id in host_id_list:
        log_data = _load_job_log(client, job_instance_id, step_instance_id, bk_host_id)
        if isinstance(log_data, dict):
            log_rows = [log_data]
        elif isinstance(log_data, list):
            log_rows = log_data
        else:
            log_rows = []

        for row in log_rows:
            if not isinstance(row, dict):
                continue
            record = BackupRecord.objects.create(
                bk_host_id=bk_host_id,
                bk_file_dir=search_path,
                bk_file_suffix=suffix,
                bk_backup_name=row.get("bk_backup_name", ""),
                bk_file_create_time=row.get("bk_file_create_time", ""),
                bk_file_operator=username,
                bk_job_link=job_link,
            )
            created_records.append(record.id)

    return _json_response(True, {"record_ids": created_records})


@api_login_exempt
def get_backup_record(request):
    """Return backup records ordered by latest first."""
    return _json_response(
        True,
        list(BackupRecord.objects.all().order_by("-id").values()),
    )
