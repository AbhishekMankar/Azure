# Azure End-to-End Data Engineering Project

## Overview
This project demonstrates an end-to-end data engineering pipeline built on **Microsoft Azure**, covering data ingestion, transformation, analytics, and visualization.  
It follows industry best practices for **security, scalability, and Git-based CI/CD**.

The pipeline ingests data using Azure Data Factory, processes it using Databricks with a medallion architecture, exposes curated data through Azure Synapse Analytics, and visualizes insights using Power BI.

---

## Architecture
**Services Used**
- Azure Data Factory (ADF)
- Azure Data Lake Storage Gen2 (ADLS)
- Azure Databricks
- Azure Synapse Analytics (Serverless SQL)
- Power BI
- GitHub (version control)

**Data Flow**
1. Data ingestion using Azure Data Factory  
2. Raw data stored in Azure Data Lake  
3. Data transformation using Databricks (Bronze → Silver → Gold)  
4. Analytics using Synapse Serverless SQL  
5. Reporting and dashboards using Power BI  

---
The repository is organized by Azure service to reflect an end-to-end data engineering workflow.

## Repository Structure

```text
Azure/
├── adf/            # Azure Data Factory pipelines and ARM templates
├── Databricks/     # Databricks notebooks (Silver / Gold layers)
├── Synapse/        # Synapse SQL scripts and views
├── powerbi/        # Power BI reports
├── architecture/   # Architecture diagrams
├── docs/           # Documentation
└── README.md
```


---

## Data Ingestion – Azure Data Factory
- Parameterized pipelines for scalable ingestion
- Lookup and ForEach activities for dynamic processing
- Secure integration with Azure Data Lake
- Git-enabled ADF for version-controlled pipelines

---

## Data Processing – Azure Databricks
- Implemented **Medallion Architecture**
  - Bronze: Raw ingestion
  - Silver: Cleaned and transformed data
  - Gold: Aggregated and analytics-ready data
- Secure access to ADLS using **Azure AD OAuth**
- Secrets managed via **Databricks Secret Scopes**
- Notebooks version-controlled using GitHub integration

---

## Analytics – Azure Synapse Analytics
- Serverless SQL used to query curated data directly from Data Lake
- External tables and views created on transformed datasets
- Synapse workspace connected to GitHub for CI/CD

---

## Visualization – Power BI
- Connected to Synapse Serverless SQL endpoints
- Interactive dashboards built on Gold-layer data
- Optimized for performance and cost efficiency

---

## Security & Governance
- OAuth authentication using Azure AD App Registration
- Role-based access control (RBAC)
- Secrets stored securely (no hard-coded credentials)
- GitHub used for auditing and collaboration

---

## CI/CD & Version Control
- Single GitHub repository for all Azure services
- Separate folders for ADF, Databricks, Synapse, and Power BI
- Collaboration and publish branches enabled
- Clean separation of development and deployment artifacts

---

## Key Skills Demonstrated
- Azure Data Engineering
- ETL / ELT pipeline design
- Databricks & Spark transformations
- Synapse Serverless SQL
- Secure authentication (OAuth, IAM)
- Git-based CI/CD for data platforms

---

## Author
**Abhishek Mankar**  
GitHub: https://github.com/AbhishekMankar

