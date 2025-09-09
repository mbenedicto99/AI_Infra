# ==== EKS HPA with Custom Metric (rps) - Quick POC ====
# Requisitos: kubectl, helm, python3, pip, acesso ao cluster (contexto atual)
# Namespace dos componentes de monitoramento (Prometheus/Adapter/Pushgateway)
NAMESPACE_MON ?= monitoring
# Namespace do app de exemplo
NAMESPACE_APP ?= default

RELEASE_MON ?= monitoring
RELEASE_ADAPTER ?= prometheus-adapter

# URL do Pushgateway no cluster (Chart do kube-prometheus-stack)
PUSHGATEWAY ?= http://$(RELEASE_MON)-prometheus-pushgateway.$(NAMESPACE_MON).svc.cluster.local:9091

.PHONY: poc setup monitoring adapter app hpa feed dash verify metrics clean nuke

poc: setup monitoring adapter app hpa ## Sobe toda a POC
	@echo "POC instalada. Execute: make feed (em outro terminal) para simular tráfego e ver o HPA agir."

setup: ## Instala dependências Python locais
	python3 -m pip install --upgrade pip
	python3 -m pip install -r requirements.txt

monitoring: ## Instala kube-prometheus-stack + Pushgateway
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
	helm repo update
	helm upgrade --install $(RELEASE_MON) prometheus-community/kube-prometheus-stack \
		-n $(NAMESPACE_MON) --create-namespace \
		--set prometheus-pushgateway.enabled=true

adapter: ## Instala/atualiza o Prometheus Adapter com regra de métrica customizada "rps"
	helm upgrade --install $(RELEASE_ADAPTER) prometheus-community/prometheus-adapter \
		-n $(NAMESPACE_MON) -f k8s/adapter-values.yaml

app: ## Aplica deployment e service de exemplo (orders)
	kubectl apply -n $(NAMESPACE_APP) -f k8s/orders-deploy.yaml
	kubectl apply -n $(NAMESPACE_APP) -f k8s/orders-svc.yaml

hpa: ## Aplica HPA baseado em métrica customizada "rps" associada ao Service 'orders'
	kubectl apply -n $(NAMESPACE_APP) -f k8s/hpa-orders.yaml

feed: ## Inicia gerador sintético empurrando http_requests_total -> Pushgateway (gera 'rps' no Adapter)
	python3 scripts/synth_rps.py \
		--service orders \
		--namespace $(NAMESPACE_APP) \
		--pushgateway $(PUSHGATEWAY) \
		--min 20 --max 200 --period 300 --duration 0

dash: ## Port-forward do Grafana (login padrão admin/prom-operator; altere após)
	@echo "Abrindo Grafana em http://localhost:3000 ..."
	kubectl -n $(NAMESPACE_MON) port-forward svc/$(RELEASE_MON)-grafana 3000:80

verify: ## Verifica se a métrica customizada 'rps' está publicada pelo Adapter
	@echo "Listando métricas em custom.metrics.k8s.io ..."
	kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1" | head -n 50 || true
	@echo "\nConsultando 'rps' para o Service 'orders' no namespace $(NAMESPACE_APP) ..."
	kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/$(NAMESPACE_APP)/services/*/rps" | head -n 50 || true

metrics: ## Port-forward Prometheus e Pushgateway para inspeção local
	@echo "Abrindo Prometheus em http://localhost:9090 e Pushgateway em http://localhost:9091 ..."
	kubectl -n $(NAMESPACE_MON) port-forward svc/$(RELEASE_MON)-kube-prometheus-prometheus 9090 & \
	kubectl -n $(NAMESPACE_MON) port-forward svc/$(RELEASE_MON)-prometheus-pushgateway 9091

clean: ## Remove app e HPA
	-kubectl delete -n $(NAMESPACE_APP) -f k8s/hpa-orders.yaml
	-kubectl delete -n $(NAMESPACE_APP) -f k8s/orders-svc.yaml
	-kubectl delete -n $(NAMESPACE_APP) -f k8s/orders-deploy.yaml

nuke: clean ## Remove monitoring e adapter (cuidado)
	-helm uninstall $(RELEASE_ADAPTER) -n $(NAMESPACE_MON)
	-helm uninstall $(RELEASE_MON) -n $(NAMESPACE_MON)
