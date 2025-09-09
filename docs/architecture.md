---
config
    theme: redux
---

flowchart TB

  subgraph RT[Runtime and Telemetry]
    U[Users] --> LB[ALB NLB]
    LB --> APP[Apps on EKS EC2 Fargate]
    APP -->|OTel SDK| COL[ADOT Collector]
    COL -- metrics --> AMP[Amazon Managed Prometheus]
    COL -- traces --> XR[AWS XRay]
    COL -- EMF metrics --> CWM[CloudWatch Metrics]
    APP -- logs --> CWL[CloudWatch Logs]
  end

  subgraph DL[Data Lake and Analytics]
    CWM -- Metric Streams --> FH[Kinesis Firehose]
    CWL -- Subscription --> FH
    FH --> S3[Amazon S3 Data Lake]
    S3 --> GL[AWS Glue Catalog]
    GL --> ATH[Athena or EMR Spark]
  end

  subgraph ML[MLOps and Forecast on SageMaker]
    ATH --> P1[Processing Features]
    P1 --> T1[Training TFT DeepAR NBEATS Prophet]
    T1 --> EV[Evaluation]
    EV --> REG[Model Registry]
    REG --> EP[Endpoint Online]
    REG --> BT[Batch Transform]
    T1 --> MON[Model Monitor]
  end

  subgraph ORQ[Orchestration and Context]
    EVS[EventBridge Schedules] --> P1
    EVS --> BT
    EVS --> L1[Lambda Capacity Planner]
    CE[Change Events] --> EVS
    CAL[BR Holidays Calendar] --> P1
  end

  subgraph ACT[Capacity and FinOps]
    EP -- short term forecast --> L1
    BT -- daily weekly forecast --> L1
    L1 --> ASG[AWS Auto Scaling]
    L1 --> HPA[EKS HPA or VPA]
    L1 --> FIN[FinOps RI Spot]
  end

  subgraph OBS[Observability]
    AMP --> AMG[Amazon Managed Grafana]
    CWM --> AMG
    S3 --> AMG
  end

  RT --> DL
  DL --> ML
  ML --> ACT
  RT --> OBS
  DL --> OBS
