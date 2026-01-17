Azure End-to-End Data Engineering Project
Overview

This project demonstrates an end-to-end data engineering pipeline on Microsoft Azure, covering data ingestion, transformation, analytics, and visualization using a modern cloud architecture. The solution follows best practices for security, scalability, and Git-based CI/CD.

The pipeline ingests raw data into Azure Data Lake, processes it using Databricks (medallion architecture), serves curated data through Azure Synapse Analytics, and visualizes insights in Power BI.

Architecture

Services Used:

Azure Data Factory (ADF)

Azure Data Lake Storage Gen2 (ADLS)

Azure Databricks

Azure Synapse Analytics (Serverless SQL)

Power BI

GitHub (version control & CI/CD)

High-level flow:

Data ingestion using Azure Data Factory

Secure storage in Azure Data Lake (Raw zone)

Data transformation using Databricks (Bronze → Silver → Gold)

Analytics using Synapse Serverless SQL

Reporting and visualization in Power BI
