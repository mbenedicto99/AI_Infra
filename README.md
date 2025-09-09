# Previsão de Demanda & Capacidade na AWS com OpenTelemetry e IA

> Projeto de referência (POC → Prod) para prever **demanda** (RPS, filas, tráfego) e **capacidade** (CPU/Mem/GPU, pods, nós, ASG) usando **OpenTelemetry**, **AWS** e modelos de IA (Prophet, DeepAR, TFT, N-BEATS). Inclui coleta de telemetria, data lake histórico, MLOps com SageMaker, e acionamento automático de políticas de capacidade (Auto Scaling/HPA) respeitando SLOs.

---

## ✨ Objetivos
- **Prever demanda** por serviço, região e recurso (horizonte: 15min–7 dias).
- Traduzir previsão em **políticas de capacidade** (min/max/step scaling, scheduled actions, HPA targets).
- **Reduzir custo** (rightsizing, evitar over/under-provisioning) mantendo **SLO/SLI**.
- Prover **governança**: versionamento de dados/modelos, auditoria de decisões e observabilidade do pipeline.

## 🏗️ Arquitetura (alto nível)

```mermaid
flowchart LR
  subgraph Runtime & Telemetry
    A[Aplicações em EKS/EC2/Fargate]-->B[OpenTelemetry Collector (ADOT)]
    B-- Prometheus Remote Write -->C[Amazon Managed Prometheus (AMP)]
    B-- Traces -->D[AWS X-Ray]
    B-- EMF Metrics -->E[Amazon CloudWatch]
    A-- Logs -->F[CloudWatch Logs]
  end

  subgraph Data Lake & Analytics
    E-- Metric Streams -->G[Kinesis Firehose]
    F-- Subscription ->G
    G-->H[(Amazon S3 Data Lake)]
    H<-->I[AWS Glue Data Catalog]
    I-->J[Athena/EMR/Spark]
  end

  subgraph MLOps & Forecast
    J-->K[SageMaker Processing/Training]
    K-->L[Model Registry]
    L-->M[SageMaker Endpoint (Online)]
    L-->N[SageMaker Batch Transform]
    O[EventBridge Scheduler]-->K
    O-->P[Lambda - Orquestração de Ações]
  end

  subgraph Capacity Actions
    M-- Previsão (curto prazo) -->P
    N-- Previsão (janela diária) -->P
    P-->Q[AWS Auto Scaling (ASG/ECS)]
    P-->R[EKS HPA/VPA via Custom Metrics]
    P-->S[Reserved/Spot Planner (FinOps)]
  end

  C-->T[Grafana (AMG)]
  E-->T
  H-->T
```

**Notas-chave**
- **Coleta**: ADOT (AWS Distro for OpenTelemetry) para métricas (AMP/CloudWatch), traces (X-Ray) e logs (CloudWatch).
- **Histórico**: CloudWatch **Metric Streams** + Logs → Firehose → **S3** (Parquet/partitionado) → **Athena**.
- **Modelagem**: **SageMaker** com bibliotecas `GluonTS/Darts/Prophet`. Model Monitor para drift.
- **Ação**: **Lambda** converte previsões em ações (ASG scheduled scaling, HPA target updates) via **EventBridge**.

---

## ✅ Casos de uso prioritários
- **Autoscaling preditivo** de web/API (RPS/latência → pods/nodes/ASG).
- **Planejamento de janelas**: madrugada, almoço, campanhas, feriados (BR).
- **Rightsizing**: limites de CPU/Mem/GPU por workload.
- **Custo**: evitar picos on-demand, sugerir Spot/RI conforme sazonalidade.

## 📥 Fontes de dados mínimas
- **Métricas**: `http_requests_total`, `latency_ms`, `queue_depth`, `cpu_usage`, `memory_working_set`, `gpu_utilization`.
- **Dimensões** (labels): `service`, `env`, `region`, `pod/node`, `version` (commit/deploy).
- **Eventos**: deploys/feature-flags/reindex/batch em **EventBridge** (calendário de mudanças).
- **Calendário**: feriados nacionais/estaduais (BR) + eventos de negócio.
- **(Opcional)**: **CUR/Cost Explorer** para correlação demanda ↔ custo (FinOps).

---

## 🧠 Modelos de IA (recomendados por horizonte/uso)
- **Baselines** (sempre incluir): Sazonal diária/semana, Naive/Drift; para benchmarking e guard-rails.
- **Curto prazo (5–120 min)**: **TFT** (Temporal Fusion Transformer), **TCN/LSTM**, **N-BEATS** → captura sazonalidade intradiária e choques.
- **Daily/Weekly**: **DeepAR** (probabilístico), **Prophet** (interpretação forte, feriados).
- **Probabilístico**: quantis τ∈{0.1,0.5,0.9} e **CRPS** para risco de under/over-provisioning.
- **Multivariado**: features exógenas (deploys, temperatura, campanhas).

**Métricas**: **WAPE/MASE/SMAPE**, **RMSE**, **Pinball Loss** (quantis), **CRPS**.  
**Validação**: backtesting com **rolling-origin** (janelas deslizantes) e **gap** pós-treino.

---

## 📂 Estrutura do repositório
```
.
├── infra/                 # Terraform (S3, Glue, Athena, AMP, AMG, Firehose, Roles, SM)
├── otel/                  # Manifests ADOT p/ EKS e otel-collector.yaml
├── data/                  # Esquemas, amostras Parquet/CSV (mock)
├── notebooks/             # Exploração, EDA, protótipos (Darts/GluonTS)
├── src/
│   ├── fe/                # Feature engineering (calendário, eventos, agregações)
│   ├── train/             # Scripts de treino (SageMaker Training Toolkit)
│   ├── infer/             # Handlers (endpoint/batch), pós-processamento
│   ├── actions/           # Cálculo de capacidade e chamadas AWS (ASG/HPA)
│   └── metrics/           # Avaliação e monitoramento (WandB/Evidently/SM Monitor)
├── pipelines/
│   ├── sm_pipelines.py    # Definição do pipeline (Processing->Train->Eval->Register->Deploy)
│   └── eventbridge.json   # Schedulers de retraining e batch forecasts
├── tests/                 # Unit/e2e (pytest)
├── Makefile
└── README.md
```

---

## 🔧 Infraestrutura (Terraform – visão)
- **S3 Data Lake** (camadas `raw/processed/predictions`, partition by `dt=YYYY-MM-DD`).
- **Glue**: Database + Crawlers para Parquet (métricas/logs).
- **Athena**: Workgroup + Named Queries.
- **CloudWatch Metric Streams** → **Firehose** → S3 (Parquet).
- **CloudWatch Logs Subscription** → Firehose → S3.
- **AMP/AMG** para métricas e dashboards.
- **SageMaker**: Roles, Model Registry, Endpoints (Serverless ou M5/G4dn), Monitor.
- **EventBridge/Lambda**: orquestração de retraining/inferência/ações.
- **(Opcional)**: EKS + ADOT Addon; HPA via **custom.metrics.k8s.io** (adapter).

---

## 📡 OpenTelemetry (ADOT) – exemplo de Collector (EKS)
`otel/otel-collector.yaml` (trecho simplificado):
```yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:

exporters:
  prometheusremotewrite:
    endpoint: https://aps-workspaces.${AWS_REGION}.amazonaws.com/workspaces/${AMP_WS_ID}/api/v1/remote_write
    auth:
      authenticator: sigv4auth
  awsxray: {}
  awsemf: {}  # métricas em EMF -> CloudWatch
  logging:
    loglevel: info

extensions:
  sigv4auth: {}

service:
  extensions: [sigv4auth]
  pipelines:
    metrics:
      receivers: [otlp]
      exporters: [prometheusremotewrite, awsemf]
    traces:
      receivers: [otlp]
      exporters: [awsxray]
```

- **AMP**: dashboards em **Amazon Managed Grafana (AMG)** via Prometheus datasource.
- **CloudWatch**: habilita **Metric Streams → Firehose** para materializar histórico em S3 (treino).

---

## 🗃️ Esquema de dados no Data Lake (Parquet)
**Tabela `metrics_timeseries` (partitioned by `dt`)**
- `ts` (timestamp), `metric` (string), `value` (double)
- `service`, `env`, `region`, `pod`, `node`, `version` (strings)
- `window` (string; ex: `1m`, `5m`)
- `dt` (string; `YYYY-MM-DD`)

**Tabela `events_change`**
- `ts`, `service`, `event_type` (deploy/feature/campaign), `version`, `metadata` (json)

---

## 🔬 Feature Engineering (exemplos)
- **Calendário**: `dow`, `hour`, `is_weekend`, `is_holiday_BR`, `payday`, `campaign`.
- **Lagged/rolling**: `y(t-1…t-96)`, médias/medianas/quantis, **anomaly mask**.
- **Exógenas**: fila, latência P95, **deploy_version**, **feature_flag**.
- **Business**: volume transacional/abandonos (se disponível).

---

## 🧪 Avaliação & SLOs
- **SLO de previsão**: WAPE ≤ 15% intradiário; cobertura de intervalos [P10,P90] ≥ 80%.
- **SLO operacional**: ≤ 0.5% de violações de **latência P95**/erro por under-provision.
- **A/B de política**: Causal Impact/Uplift para validar ganhos de custo/MTTR.

---

## 🤖 Pipeline MLOps (SageMaker Pipelines)
1. **Processing** (Athena/Spark): materializa dataset por `service/env/region` (janelas e features).
2. **Training**: treina **TFT/DeepAR/N-BEATS/Prophet** + **baseline sazonal**.
3. **Evaluation**: backtesting (rolling-origin), calcula métricas; gera relatórios.
4. **Register**: versiona no **Model Registry** com tags (`service=api-x`, `region=sa-east-1`).
5. **Deploy**: 
   - **Online**: Endpoint (Serverless ou provisionado).
   - **Batch**: Batch Transform diário para janelas longas.
6. **Monitor**: **Model Monitor** (drift), alarmes em **CloudWatch**.

---

## 🖧 Inferência → Ações de Capacidade
- **Lambda `capacity_planner`** (disparado por EventBridge ou S3 put):
  - Converte previsão probabilística em **reservas**: usa `P90` para evitar under-provision.
  - **ASG/ECS**: cria/atualiza **Scheduled Actions** (ex.: 09:00–20:00 scale-out).
  - **EKS HPA**: ajusta target (RPS por pod / CPU target) via **K8s API** e **custom metrics**.
  - **FinOps**: sugere **Spot/RI** quando estabilidade > limiar (ex.: WAPE < 10% 30d).

---

## 🧾 Exemplo de Athena (agregação 5-min, API `orders`)
```sql
CREATE OR REPLACE VIEW v_orders_rps_5m AS
SELECT
  date_trunc('minute', ts) AS ts_min,
  service,
  region,
  env,
  approx_percentile(value, 0.5) AS rps_p50,
  approx_percentile(value, 0.95) AS rps_p95
FROM metrics_timeseries
WHERE metric = 'http_requests_per_second'
  AND service = 'orders'
  AND env = 'prod'
  AND dt BETWEEN date_format(date_add('day', -30, current_date), '%Y-%m-%d') AND date_format(current_date, '%Y-%m-%d')
GROUP BY 1,2,3,4;
```

---

## 🧑‍💻 Treino (exemplo Python – SageMaker + GluonTS/DeepAR)
```python
# src/train/train_deepar.py (resumo)
import json, os, pandas as pd, numpy as np
from gluonts.dataset.common import ListDataset
from gluonts.mx import Trainer
from gluonts.model.deepar import DeepAREstimator
from gluonts.evaluation.backtest import make_evaluation_predictions

FREQ = "5min"
PRED_LEN = 24  # 2h à frente (5m * 24)

def load_series(path):
    df = pd.read_parquet(path)
    df = df.sort_values("ts")
    target = df["rps_p95"].astype(float).values
    start = pd.Timestamp(df["ts"].iloc[0], freq=FREQ)
    return ListDataset([{"start": start, "target": target}], freq=FREQ)

train_ds = load_series("/opt/ml/input/data/train/orders.parquet")
estimator = DeepAREstimator(freq=FREQ, prediction_length=PRED_LEN, trainer=Trainer(epochs=20))
predictor = estimator.train(train_ds)

# Salvar artefatos
predictor.serialize(Path("/opt/ml/model"))
```

---

## 🟢 Inferência online (handler – SageMaker Endpoint)
```python
# src/infer/handler.py
import json, numpy as np, pandas as pd
from gluonts.model.predictor import Predictor
from pathlib import Path

model = None

def model_fn(model_dir):
    global model
    model = Predictor.deserialize(Path(model_dir))
    return model

def input_fn(request_body, request_content_type):
    payload = json.loads(request_body)
    # payload: {"recent_values": [...], "exog": {...}}
    return payload

def predict_fn(payload, model):
    pred = model.predict([{"start": pd.Timestamp.now(), "target": payload["recent_values"]}])
    forecast = next(pred)
    return {"p10": forecast.quantile(0.1).tolist(),
            "p50": forecast.quantile(0.5).tolist(),
            "p90": forecast.quantile(0.9).tolist()}

def output_fn(prediction, accept):
    return json.dumps(prediction), "application/json"
```

---

## 🧮 Política de capacidade (exemplo simplificado)
```python
# src/actions/capacity.py
def pods_needed(p90_rps, rps_per_pod, headroom=0.2):
    return int(np.ceil((p90_rps / rps_per_pod) * (1 + headroom)))

def asg_desired(pods, pods_per_node):
    return int(np.ceil(pods / pods_per_node))
```

---

## 🔒 Segurança & Governança
- **IAM mínimo necessário** (SageMaker, Firehose, Glue/Athena, CloudWatch, AMP, EKS).
- **Criptografia**: S3 (SSE-KMS), Athena spill, logs, endpoints (VPC + KMS).
- **Rede**: Endpoints VPC para S3/STS/SM; bloquear Internet em produção.
- **Auditoria**: CloudTrail + Athena Lake para trilhas de decisão (previsão → ação).

---

## 💰 Custos (estimativa POC)
- **AMP/AMG**: ingest/dashboards conforme cardinalidade (controle de labels!).
- **Firehose + S3 + Athena**: baixo custo por GB + consultas sob demanda.
- **SageMaker**: treino eventual (spot) + **Serverless Inference** p/ baixos picos.
- **X-Ray/CloudWatch**: dimensionar retenção; metric streams ≈ US$ 0.01/1k métricas + Firehose.

---

## ▶️ Como executar (POC)
1. **Pré-requisitos**: `awscli`, `terraform`, `kubectl`, `helm`, Python 3.11.
2. **Provisionar**: `cd infra && terraform init && terraform apply` (defina `region`, `bucket_base`, `amp_ws`, `kms_key`).
3. **ADOT** (EKS): `helm repo add aws-observability https://aws-observability.github.io/helm-charts && helm install adot aws-observability/aws-otel-collector -f otel/otel-collector.yaml`.
4. **Metric Streams** → Firehose → S3 (Terraform já cria).
5. **Glue Crawlers** → rodar e verificar tabelas `metrics_timeseries`/`events_change`.
6. **Athena** → criar view `v_orders_rps_5m` e validar dados.
7. **SageMaker Pipeline**: `python pipelines/sm_pipelines.py --region sa-east-1 --service orders`.
8. **Endpoint**: ao terminar, obter o `EndpointName` e testar com `src/infer/client.py`.
9. **Ações**: habilitar `EventBridge` + `Lambda capacity_planner` (variáveis: `service`, `rps_per_pod`).

---

## 🧭 Decisões de projeto (trade-offs)
- **AMP + CloudWatch** juntos: AMP para observabilidade em tempo real; CloudWatch para **Metric Streams** (S3 histórico).  
- **Probabilístico por padrão**: minimiza **risco de under-provision** operacional.
- **P50 vs P90**: usar **P90** para produção; **P50** para eficiência sob SLO folgado.
- **Explainability**: Prophet para leitura de efeitos; TFT/N-BEATS para acurácia.

---

## 🐉 Riscos & Antipadrões
- **Cardinalidade de labels** explode custos (AMP/CloudWatch/Glue). Normalize `service/env`.
- **Treinar com dados “sujos” (incidentes)** sem máscara → viés.
- **Feedback loops**: autoscaling afeta métricas; mantenha “hold-out” e controle.
- **Falta de SLO**: IA não substitui governança de SLI/SLO e runbooks.

---

## 🗺️ Roadmap
- [ ] Adapter HPA (custom metrics) e política híbrida (reactive + predictive).
- [ ] Integração **Cost & Usage Report** (CUR) para prever **custo** junto da **demanda**.
- [ ] Experimentação causal (Causal Impact) para provar ganho de política.
- [ ] Suporte a GPUs (inference servers) e jobs batch elásticos (EMR/EKS/Karpenter).
- [ ] RL para tuning de políticas de scaling sob SLO e custo (PPO).

---

## 📚 Referências rápidas
- **ADOT/OTel**: semantic conventions (HTTP, DB, messaging).
- **SageMaker**: DeepAR/TFT/N-BEATS (via GluonTS/Darts), Model Monitor.
- **AWS**: CloudWatch **Metric Streams**, **AMP/AMG**, **EventBridge**, **Auto Scaling**, **EKS HPA**.

---

## 📝 Licença
MIT (ajuste conforme sua necessidade).
