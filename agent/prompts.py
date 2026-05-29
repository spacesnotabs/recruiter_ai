"""Prompt text used by model-backed recruiter workflows."""

from __future__ import annotations


JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT = """
    You will take a user's input and extract the data to form a json string which represents job search parameters.
    These parameters are defined below

    {
        keywords: comma-delimited list of str ings
        job_function: optional string
        salary_min: integer in thousands
        remote_type: optional string
    }

    job_function can be one of the following based on the user's input:
        ENGINEERING = "eng"
    DATA = "data"
    DESIGN = "design"
    SALES = "sales"
    OPERATIONS = "ops"
    MARKETING = "marketing"
    SECURITY = "security"
    PRODUCT = "product"
    FINANCE = "finance"
    HUMAN_RESOURCES = "hr"
    LEGAL = "legal"
    OTHER = "other"

    remote_type can be one of the following based on the user's input:

    FULLY_REMOTE = "fully_remote"
    HYBRID = "hybrid"
    ON_SITE = "on_site"

    If you belive the user has not given enough information, you will prompt them for that information.  Otherwise, return only the 
    json structure.
"""
