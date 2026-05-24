# -*- coding: utf-8 -*-
from django.db import models


class BizInfo(models.Model):
    """Cached CMDB business metadata."""

    bk_biz_id = models.IntegerField(unique=True)
    bk_biz_name = models.CharField(max_length=50)

    def __str__(self):
        return "{}-{}".format(self.bk_biz_id, self.bk_biz_name)


class BackupRecord(models.Model):
    """Backup operation record created from JOB execution logs."""

    bk_host_id = models.IntegerField(verbose_name="host id")
    bk_file_dir = models.CharField(verbose_name="file directory", max_length=1024)
    bk_file_suffix = models.CharField(verbose_name="file suffix", max_length=255)
    bk_backup_name = models.CharField(verbose_name="backup file name", max_length=1024)
    bk_file_create_time = models.CharField(verbose_name="backup time", max_length=30)
    bk_file_operator = models.CharField(verbose_name="backup operator", max_length=30)
    bk_job_link = models.CharField(verbose_name="JOB result link", max_length=255)

    class Meta:
        verbose_name = "backup record"
        verbose_name_plural = "backup records"

    def __str__(self):
        return "{}-{}".format(self.bk_host_id, self.bk_backup_name)
