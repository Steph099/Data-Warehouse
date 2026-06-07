"""Spark analytics jobs.

These modules run INSIDE the containerized Spark service via spark-submit and must
stay self-contained (PySpark + stdlib only) — they do not import the acme_dwh package.
"""
