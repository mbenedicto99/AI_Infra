# EKS HPA com Métrica Customizada (rps) — POC

Este pacote sobe rapidamente um stack de observabilidade no cluster (Prometheus/Grafana/Pushgateway),
instala o **Prometheus Adapter** com uma regra que expõe `rps` em `custom.metrics.k8s.io`, cria um
**Deployment/Service** de exemplo (`orders`) e um **HPA** que escala pelo alvo de `rps`.

A carga é gerada por um **simulador** que empurra `http_requests_total` (counter) para o Pushgateway.
O Adapter transforma em `rps` via `rate()` e o HPA utiliza essa métrica.

## Passos rápidos

1. Pré-requisitos: `kubectl`, `helm`, `python3` e contexto apontando para seu cluster (EKS).
2. `make poc` — instala monitoring, adapter, app e HPA.
3. `make feed` — inicia o gerador sintético (Ctrl+C para parar).
4. `make verify` — checa se `rps` aparece na API `custom.metrics.k8s.io`.
5. `make dash` — Grafana local em http://localhost:3000 (login inicial: admin/prom-operator).

## Ajustes úteis

- Valor alvo do HPA: edite `k8s/hpa-orders.yaml` (`target.value: "50"`).
- Amplitude/período da carga: flags `--min`, `--max`, `--period` em `make feed`.
- Namespace do app: `NAMESPACE_APP` no Makefile (padrão `default`).
- Para limpar: `make clean` (app/HPA) ou `make nuke` (remove tudo, inclusive monitoring/adapter).
