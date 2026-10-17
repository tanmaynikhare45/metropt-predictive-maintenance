::: {align="center"}
# 🚇 Real-Time Predictive Maintenance and forecasting for Metro Train Compressors

### AI-powered compressor monitoring, anomaly detection, and failure-risk analysis

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/Machine%20Learning-Predictive%20Maintenance-8A2BE2" alt="Machine Learning">
  <img src="https://img.shields.io/badge/Apache%20Kafka-Streaming-231F20?logo=apachekafka&logoColor=white" alt="Apache Kafka">
  <img src="https://img.shields.io/badge/Docker-Containers-2496ED?logo=docker&logoColor=white" alt="Docker">
</p>
**Project status:** 🚧 In Development
:::

------------------------------------------------------------------------

## 📌 Overview

Unexpected compressor failures can disrupt metro operations and increase
maintenance costs. This project uses the **MetroPT-3 dataset** to
explore machine learning methods for detecting unusual compressor
behaviour, estimating future failure risk, and forecasting sensor
readings.

The planned platform combines ML models, a FastAPI backend, a React
dashboard, time-series storage, and a simulated streaming pipeline.

## ✨ Key Features

  -----------------------------------------------------------------------
  Feature                             Description
  ----------------------------------- -----------------------------------
  🔍 Anomaly Detection                Identify unusual behaviour using
                                      Isolation Forest and an LSTM
                                      Autoencoder

  ⚠️ Failure-Risk Prediction          Estimate risk over configurable
                                      future time horizons

  📈 Sensor Forecasting               Forecast signals such as pressure
                                      and oil temperature

  ⚡ Streaming Simulation             Replay historical sensor readings
                                      through Apache Kafka

  📊 Monitoring Dashboard             Visualise sensor trends,
                                      predictions, equipment health, and
                                      alerts

  🧪 Digital Twin Prototype           Simulate sensor changes and compare
                                      model outputs

  🔔 Smart Notifications              Send configured maintenance alerts
                                      through Slack webhooks

  🐳 Containerisation                 Package services with Docker and
                                      Docker Compose
  -----------------------------------------------------------------------

> 🚧 Features are being developed incrementally. Only mark a feature as
> complete after implementation and testing.

## 🏗️ System Architecture

The diagram below shows the **planned architecture** and how data moves
from the dataset through processing, ML inference, APIs, dashboards, and
alerts.

``` mermaid
flowchart TB
    A[("📁 MetroPT-3 Dataset<br/>CSV Sensor Data")] --> B["🧹 Data Processing<br/>Pandas · NumPy"]
    B --> C["⚙️ Feature Engineering"]
    C --> D["🤖 ML Models<br/>Isolation Forest · LSTM Autoencoder"]
    C --> E["📈 Failure Prediction<br/>Random Forest · XGBoost"]
    C --> F["🔮 Sensor Forecasting<br/>Prophet · Optional N-BEATS"]

    A --> G["⚡ Kafka Producer<br/>Historical Data Replay"]
    G --> H["📨 Kafka Consumer"]
    H --> I[("🗄️ TimescaleDB<br/>Time-Series Storage")]
    H --> D
    H --> E
    H --> F

    D --> J["🚀 FastAPI Backend"]
    E --> J
    F --> J
    I <--> J

    J --> K["🖥️ React Dashboard<br/>Recharts"]
    J --> L["🔔 Alert Service"]
    L --> M["💬 Slack Webhook"]

    classDef source fill:#e8f1ff,stroke:#356ac3,color:#152b4a
    classDef ml fill:#f1e8ff,stroke:#805ad5,color:#29154d
    classDef infra fill:#e6fffa,stroke:#319795,color:#123b3a
    classDef ui fill:#fff4df,stroke:#d69e2e,color:#4a3410
    class A source
    class D,E,F ml
    class G,H,I infra
    class J,K,L,M ui
```

### 🔄 Data Flow

1.  📥 Load and inspect historical MetroPT-3 sensor readings.
2.  🧹 Clean timestamps, handle missing values, and engineer features.
3.  🤖 Run anomaly detection, failure-risk prediction, and forecasting.
4.  ⚡ Replay historical readings through Kafka to simulate streaming.
5.  🗄️ Store time-series readings and outputs in TimescaleDB.
6.  🚀 Serve readings and predictions through FastAPI.
7.  📊 Display results in React and send configured alerts through
    Slack.

> **Important:** Kafka replay simulates live ingestion. It does not
> connect to an actual metro train.

## 🧰 Technology Stack

  Category              Tools
  --------------------- --------------------------------
  🐍 Programming        Python, JavaScript
  🧮 Data Processing    Pandas, NumPy
  🤖 Machine Learning   Scikit-learn, PyTorch, XGBoost
  🔮 Forecasting        Prophet, optionally N-BEATS
  ⚙️ Backend            FastAPI, Uvicorn
  🎨 Frontend           React, Vite, Recharts, Axios
  ⚡ Streaming          Apache Kafka
  🗄️ Database           PostgreSQL, TimescaleDB
  🔔 Notifications      Slack Incoming Webhooks
  🐳 DevOps             Docker, Docker Compose
  🧪 Testing            Pytest
  🌿 Version Control    Git, GitHub

## 📂 Dataset

**MetroPT-3 --- UCI Machine Learning Repository**

🔗 [Open the dataset
page](https://archive.ics.uci.edu/dataset/791/metropt+3+dataset)

The dataset contains approximately:

-   📊 **1.5 million** sensor records
-   📡 **15** sensor signals
-   📈 **7 analog** and **8 digital** signals
-   ⚠️ **4 documented** air-leak failure events

### Example Sensors

  Sensor              Description
  ------------------- -------------------------------------
  `TP2`               Pressure measurement
  `TP3`               Pressure measurement
  `Oil_temperature`   Oil temperature
  `Motor_current`     Compressor motor current
  `COMP`              Digital compressor operating signal
  `Pressure_switch`   Digital pressure-switch signal

Failure labels are derived from documented failure intervals. Verify
these intervals against the original dataset documentation before
training or evaluating models.

## 🚀 Getting Started

### ✅ Prerequisites

-   Python 3.11 or 3.12
-   Git
-   Node.js LTS (for the frontend)
-   Docker Desktop (for containerised services)
-   VS Code (recommended)

### 1️⃣ Clone the Repository

``` bash
git clone https://github.com/<your-username>/metropt-predictive-maintenance.git
cd metropt-predictive-maintenance
```

Replace `<your-username>` with the correct GitHub username or repository
URL.

### 2️⃣ Create a Python Environment

**Windows PowerShell:**

``` powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 3️⃣ Install Dependencies

If the repository contains `requirements.txt`:

``` bash
pip install -r requirements.txt
```

Otherwise, install the dependencies required by the component you are
developing.

### 4️⃣ Download the Dataset

Place the downloaded CSV file at:

``` text
data/raw/MetroPT3(AirCompressor).csv
```

Keep raw and processed dataset files out of version control.

### 5️⃣ Explore the Data

Open:

``` text
notebooks/01_eda.ipynb
```

Select your `.venv` Python kernel and run the notebook cells.

### 6️⃣ Run the Backend

After implementing the FastAPI application and installing its
dependencies:

``` bash
uvicorn backend.main:app --reload
```

Open the interactive API documentation at:

➡️ http://127.0.0.1:8000/docs

### 7️⃣ Run the Frontend

After setting up the React application:

``` bash
cd frontend
npm install
npm run dev
```

Vite will display the local frontend URL in your terminal.

> These commands require the corresponding files and services to exist
> and be configured. They do not mean every component is already
> runnable.

## 🔌 Planned API Endpoints

  -----------------------------------------------------------------------
  Method                  Endpoint                Purpose
  ----------------------- ----------------------- -----------------------
  `GET`                   `/health`               ❤️ Check API status

  `GET`                   `/sensors`              📡 Retrieve sensor
                                                  readings

  `GET`                   `/predictions`          🤖 Retrieve anomaly and
                                                  failure-risk outputs

  `GET`                   `/forecast`             📈 Retrieve sensor
                                                  forecasts

  `GET`                   `/alerts`               🔔 Retrieve alert
                                                  history

  `GET`                   `/health-index`         🩺 Retrieve equipment
                                                  health summary

  `POST`                  `/whatif`               🧪 Evaluate a simulated
                                                  sensor scenario
  -----------------------------------------------------------------------

These endpoints are planned. Request parameters and response schemas
should be documented as each endpoint is implemented.

## 🗺️ Development Roadmap

-   [ ] 🛠️ Set up the project environment and repository
-   [ ] 📊 Complete exploratory data analysis
-   [ ] 🏷️ Validate failure intervals and prepare labels
-   [ ] 🔍 Implement Isolation Forest anomaly detection
-   [ ] 🧠 Develop and evaluate an LSTM Autoencoder
-   [ ] ⚠️ Train and evaluate failure-risk models
-   [ ] 📈 Implement sensor forecasting
-   [ ] 🧩 Build reusable feature-processing and inference modules
-   [ ] 🚀 Integrate FastAPI and TimescaleDB
-   [ ] ⚡ Implement Kafka historical data replay
-   [ ] 🎨 Build the React monitoring dashboard
-   [ ] 🔔 Integrate Slack alerts and alert history
-   [ ] 🧪 Prototype the digital twin and what-if simulation
-   [ ] 🐳 Add tests and Docker configuration
-   [ ] 📸 Add verified results, screenshots, and a demo
-   [ ] ☁️ Explore cloud deployment and Kubernetes

## 📊 Model Evaluation

Because compressor failures are rare, accuracy alone is not sufficient.

  -----------------------------------------------------------------------
  Component                           Metrics
  ----------------------------------- -----------------------------------
  🔍 Anomaly Detection                Precision, Recall, F1-score,
                                      PR-AUC, false-alarm episodes

  ⚠️ Failure Prediction               Precision, Recall, F1-score,
                                      PR-AUC, detection lead time

  📈 Forecasting                      MAE, sMAPE, prediction-interval
                                      coverage

  ⚡ Streaming                        Throughput, processing latency,
                                      failed-message count

  🚀 API                              Response latency, endpoint tests,
                                      error handling
  -----------------------------------------------------------------------

Use chronological, failure-aware validation to reduce data leakage.
Report the test period, thresholds, and limitations with the results.

📌 **No model-performance figures are claimed until experiments have
been run and verified.**

## 🖼️ Screenshots & Demo

Add real screenshots here as components become available.

  Screenshot                   Status
  ---------------------------- -------------
  📊 Dashboard Overview        Coming soon
  🔍 Anomaly Detection         Coming soon
  ⚠️ Failure-Risk Prediction   Coming soon
  📈 Sensor Forecasting        Coming soon
  🔔 Alert History             Coming soon

## ⚠️ Limitations

-   The dataset contains only four documented failure events, limiting
    evaluation reliability.
-   Results may not generalise to other trains or compressor systems.
-   Historical replay simulates streaming; it is not a live train
    connection.
-   Normal compressor operating cycles may resemble anomalies.
-   Failure-risk scores are estimates, not guaranteed probabilities.
-   Digital-twin outputs and remaining-useful-life estimates are
    experimental.
-   Maintenance recommendations require validation by qualified
    engineering personnel.

## 🔐 Security

-   🔑 Never commit `.env` files, database credentials, or Slack webhook
    URLs.
-   📁 Exclude raw data, generated files, and virtual environments from
    Git where appropriate.
-   🛡️ Use environment variables or a secret manager for sensitive
    configuration.
-   🔒 Protect deployed APIs and databases with appropriate
    authentication and network security.

## 📚 References

-   📂 [MetroPT-3 Dataset ---
    UCI](https://archive.ics.uci.edu/dataset/791/metropt+3+dataset)
-   🤖 [Scikit-learn](https://scikit-learn.org/stable/)
-   🔥 [PyTorch](https://pytorch.org/docs/stable/)
-   ⚙️ [FastAPI](https://fastapi.tiangolo.com/)
-   ⚡ [Apache Kafka](https://kafka.apache.org/documentation/)
-   🗄️ [TimescaleDB](https://docs.timescale.com/)
-   ⚛️ [React](https://react.dev/)
-   🐳 [Docker](https://docs.docker.com/)

## 👨‍💻 Author

**Tanmay Nikhare**

🐙 GitHub: [tanmaynikhre45](https://github.com/tanmaynikhre45)

------------------------------------------------------------------------


⭐ **If you find this project interesting, consider starring the
repository!**

*Built for learning, experimentation, and portfolio demonstration. This
project is not a replacement for professional railway maintenance
procedures or safety-critical engineering systems.*
:::
