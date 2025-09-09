#!/usr/bin/env python3
# Gera tráfego sintético como counter Prometheus (http_requests_total)
# e envia para o Pushgateway. O Prometheus Adapter transforma em 'rps' via rate().

import argparse, math, random, time, signal, sys
from datetime import datetime
from prometheus_client import CollectorRegistry, Counter, push_to_gateway

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--pushgateway", required=True, help="URL do Pushgateway (ex: http://pushgateway.monitoring:9091)")
    p.add_argument("--service", default="orders")
    p.add_argument("--namespace", default="default")
    p.add_argument("--job", default="synthetic-traffic")
    p.add_argument("--period", type=int, default=300, help="Período da senóide principal (s)")
    p.add_argument("--min", dest="rps_min", type=float, default=10.0, help="RPS mínimo")
    p.add_argument("--max", dest="rps_max", type=float, default=200.0, help="RPS máximo")
    p.add_argument("--spike", type=float, default=1.6, help="Multiplicador de pico esporádico")
    p.add_argument("--duration", type=int, default=0, help="Duração em segundos (0 = infinito)")
    p.add_argument("--step", type=float, default=1.0, help="Intervalo de envio em segundos")
    return p.parse_args()

def main():
    args = parse_args()

    # Setup do registry local (apenas o counter que vamos enviar)
    registry = CollectorRegistry()
    req_counter = Counter("http_requests_total", "Total HTTP requests", ["service", "namespace"], registry=registry)

    total_seconds = 0
    start = time.time()

    def sigint_handler(sig, frame):
        print("\nInterrompido pelo usuário. Encerrando...")
        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)

    # Estado do contador
    c = 0.0
    while True:
        t = time.time() - start

        # Componente senoidal diária/sazonal
        base = (math.sin(2*math.pi * (t % args.period) / args.period) + 1) / 2  # [0,1]
        rps = args.rps_min + base * (args.rps_max - args.rps_min)

        # Ruído + micro variações
        rps *= (0.9 + 0.2 * random.random())

        # Picos ocasionais
        if random.random() < 0.02:
            rps *= args.spike

        # Incrementa counter conforme rps aproximado por segundo
        increment = max(0.0, rps * args.step)
        c += increment

        # Atualiza (counter só permite inc)
        # Estratégia: somar delta desde o último envio
        req_counter.labels(service=args.service, namespace=args.namespace).inc(increment)

        # Envia para o Pushgateway. Usamos labels de agrupamento job/service/namespace
        try:
            push_to_gateway(
                gateway=args.pushgateway,
                job=args.job,
                registry=registry,
                grouping_key={"service": args.service, "namespace": args.namespace}
            )
        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}Z] Falha ao enviar para Pushgateway: {e}")

        # Log simples no stdout
        if int(t) % 10 == 0:
            print(f"{datetime.utcnow().isoformat()}Z service={args.service} rps~{rps:.1f} counter+={increment:.1f} total≈{c:.0f}")

        time.sleep(args.step)
        total_seconds += args.step
        if args.duration and total_seconds >= args.duration:
            print("Duração limite atingida. Encerrando gerador.")
            break

if __name__ == "__main__":
    main()
