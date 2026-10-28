# Universal Data Collection and Research Team

## Mission
Build an extensible, reliable, and continuously improving system for collecting, analyzing, validating, and learning from diverse data sources.

## 1. Universal Data Collection
The system should support:
- Structured data: databases, tables, CSV, and Excel.
- Semi-structured data: JSON, XML, APIs, and event logs.
- Unstructured data: text, webpages, PDFs, documents, images, audio, and video.
- Metadata, timestamps, and other relevant contextual information.

## 2. Multi-Method Data Acquisition
Use appropriate, authorized methods, including:
- File ingestion and public datasets.
- Public websites and authorized APIs.
- Audio, video, image, and document extraction.
- Automated and human-assisted labeling.
- Cross-source comparison and verification.

Every collected item should retain its source, collection time, method, permissions or license information when available, quality indicators, and uncertainty.

## 3. Machine Learning and Deep Learning
Use suitable machine-learning and deep-learning methods to:
- Classify and analyze collected data.
- Detect patterns, anomalies, duplicates, and contradictions.
- Extract information and identify semantic relationships.
- Assess data quality and select effective collection methods.
- Train or fine-tune models when suitable data and computational resources are available.

## 4. Continuous Improvement
Record methods, outcomes, errors, resource usage, and lessons learned. Use this evidence to improve future collection and analysis while avoiding unsupported claims of progress.

## 5. Independent Research Management
The system should be designed to:
- Define research objectives and break them into tasks.
- Prioritize tasks and select appropriate methods.
- Execute tasks and validate results.
- Identify failures, revise approaches, and document decisions.
- Select the next task based on evidence, priorities, and available resources.
- Request human assistance when necessary.

Autonomous planning does not guarantee continuous execution; runtime and hosting requirements must be evaluated separately.

## 6. Independent Evaluation and Quality Assurance
Evaluate performance using measurable criteria, including:
- Data volume, coverage, completeness, and collection cost.
- Accuracy, consistency, duplication, and missing information.
- Appropriate model metrics, such as precision, recall, and F1 score.
- Performance on independent, previously unseen test data.
- Research completion time, failure rate, reliability, and recovery.
- Improvements or regressions compared with previous versions.

Maintain reproducible tests, separate training and evaluation data, document limitations, and preserve previous working versions. After evaluation, accept, repeat, modify, roll back, or request assistance as appropriate.

## 7. Architecture and Reliability
Develop the system in modular stages. Keep source code, documentation, configurations, experiments, and evaluation results version-controlled. Prefer reproducible workflows and openly document dependencies and resource requirements.

## 8. Privacy, Security, and Responsible Research
Collect and process data only through lawful and authorized methods. Respect privacy, access restrictions, licenses, and applicable terms. Protect credentials and sensitive information. Do not claim access to data, tools, models, or computing resources that are unavailable.

## 9. Initial Development Principles
- Start with a small, working baseline.
- Test each component before expanding the system.
- Record evidence for important decisions.
- Measure real performance instead of assuming success.
- Expand functionality incrementally.
- Prefer sustainable, low-cost resources when practical, without assuming that free services provide permanent, uninterrupted execution.

## Current Status
Project specification and repository setup are in progress. Features must be implemented and tested before being described as operational.
