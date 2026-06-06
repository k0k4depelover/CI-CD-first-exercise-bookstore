# DevOps Bootcamp — BookVault

## Tu Misión

Eres el nuevo DevOps/SysAdmin de **BookVault**, una startup que gestiona inventarios de libros. El equipo de desarrollo te entrega la aplicación ya terminada (una API REST en Python/Flask con PostgreSQL). Tu trabajo: desplegarla, protegerla, automatizarla y monitorearla.

**Todo gratis**, usando Docker, LocalStack (simula AWS) y herramientas open source.

---

## Requisitos Previos

Instalar en tu máquina local:

- Docker y Docker Compose
- Git
- AWS CLI v2
- Terraform (>= 1.5)
- Python 3.11+ (solo para correr tests)
- curl y jq

---

## Estructura del Proyecto

```
devops-bootcamp/
├── app/                    ← Código de la API (NO TOCAR)
│   ├── main.py
│   ├── wsgi.py
│   ├── requirements.txt
│   └── Dockerfile
├── tests/
│   └── test_api.py
├── nginx/
│   └── default.conf
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
├── terraform/
│   └── main.tf
├── scripts/
│   ├── backup.sh
│   └── healthcheck.sh
├── .github/workflows/
│   └── ci.yml
├── docker-compose.yml
├── .env.example
└── .gitignore
```

---

## FASE 1 — Containerización y Despliegue Local

### Tarea 1: Levantar el entorno completo

**Objetivo:** Hacer que la aplicación funcione en Docker.

**Pasos:**
1. Clonar el repo y revisar la estructura
2. Copiar `.env.example` a `.env` y ajustar los valores
3. Levantar los servicios con `docker compose up -d`
4. Verificar que la API responde: `curl http://localhost:5000/health`
5. Probar el CRUD de libros con curl

**Verificación:**
```bash
# Debe devolver {"status": "ok", ...}
curl -s http://localhost:5000/health | jq

# Debe listar los libros seed
curl -s http://localhost:5000/api/v1/books | jq

# Crear un libro
curl -s -X POST http://localhost:5000/api/v1/books \
  -H "Content-Type: application/json" \
  -d '{"title":"DevOps Handbook","author":"Gene Kim","genre":"Tech","year":2016,"stock":10}' | jq
```

### Tarea 2: Añadir Nginx como Reverse Proxy

**Objetivo:** No exponer la aplicación directamente — ponerla detrás de Nginx.

**Pasos:**
1. Añadir un servicio `nginx` al `docker-compose.yml` usando la imagen `nginx:alpine`
2. Montar `nginx/default.conf` como configuración
3. Exponer solo el puerto 80 de Nginx al host; quitar el port mapping del servicio `api`
4. Verificar que `http://localhost/health` funciona
5. Verificar que los headers de seguridad están presentes

**Verificación:**
```bash
# Debe funcionar a través de Nginx
curl -s http://localhost/api/v1/books | jq

# Debe mostrar headers de seguridad
curl -sI http://localhost/ | grep -i "x-frame"
```

---

## FASE 2 — CI/CD Pipeline

### Tarea 3: Completar el Pipeline de CI

**Objetivo:** Hacer que `.github/workflows/ci.yml` funcione.

**Pasos:**
1. Completar los TODO del archivo `ci.yml`
2. Añadir el paso de linting con flake8
3. Configurar el build de Docker
4. Añadir escaneo de seguridad con Trivy
5. Si no tienes GitHub: simular el pipeline localmente con `act` (https://github.com/nektos/act)

**Verificación:**
```bash
# Correr tests localmente primero
pip install pytest flake8
pytest tests/ -v
flake8 app/ --max-line-length=120

# Simular con act (opcional)
act push
```

### Tarea 4: Pipeline de CD — Deploy Automático

**Objetivo:** Crear un workflow de CD que despliegue automáticamente.

**Pasos:**
1. Crear `.github/workflows/cd.yml`
2. El pipeline debe: hacer build, correr tests, construir imagen Docker, hacer "deploy" (simular con docker compose)
3. Agregar un paso de rollback si el healthcheck falla post-deploy
4. Implementar versionado semántico con tags de Git

---

## FASE 3 — Infrastructure as Code (LocalStack)

### Tarea 5: Levantar LocalStack y crear infraestructura

**Objetivo:** Simular servicios AWS con LocalStack + Terraform.

**Pasos:**
1. Añadir LocalStack al `docker-compose.yml`:
   ```yaml
   localstack:
     image: localstack/localstack:latest
     ports:
       - "4566:4566"
     environment:
       - SERVICES=s3,sqs,sns,ssm,dynamodb
       - DEBUG=0
     volumes:
       - "/var/run/docker.sock:/var/run/docker.sock"
   ```
2. Levantar LocalStack: `docker compose up localstack -d`
3. Aplicar Terraform:
   ```bash
   cd terraform/
   terraform init
   terraform plan
   terraform apply -auto-approve
   ```
4. Verificar los recursos creados:
   ```bash
   aws --endpoint-url=http://localhost:4566 s3 ls
   aws --endpoint-url=http://localhost:4566 sqs list-queues
   aws --endpoint-url=http://localhost:4566 sns list-topics
   ```

### Tarea 6: Gestión de Secretos con SSM Parameter Store

**Objetivo:** No guardar contraseñas en texto plano.

**Pasos:**
1. Verificar que los parámetros SSM existen en LocalStack
2. Modificar el `docker-compose.yml` para que la app lea secretos de SSM en vez de variables de entorno hardcodeadas
3. Crear un script `scripts/fetch-secrets.sh` que lea los secretos de SSM y los exporte como variables de entorno
4. Integrar el script en el entrypoint del contenedor

**Verificación:**
```bash
# Leer el secreto desde SSM
aws --endpoint-url=http://localhost:4566 ssm get-parameter \
  --name "/bookvault/db/password" --with-decryption | jq
```

---

## FASE 4 — Admin de Sistemas

### Tarea 7: Backups Automatizados

**Objetivo:** Configurar backups periódicos de la base de datos.

**Pasos:**
1. Revisar y hacer ejecutable `scripts/backup.sh`
2. Probar el script manualmente
3. Configurar un cron job para que corra cada 6 horas
4. Verificar que el backup se sube a S3 (LocalStack)
5. Crear un script `scripts/restore.sh` para restaurar desde un backup

**Verificación:**
```bash
chmod +x scripts/backup.sh
./scripts/backup.sh

# Verificar en S3
aws --endpoint-url=http://localhost:4566 s3 ls s3://bookvault-backups/db-backups/
```

### Tarea 8: Log Management

**Objetivo:** Centralizar y rotar logs.

**Pasos:**
1. Configurar Docker logging driver con rotación:
   ```yaml
   # Añadir a cada servicio en docker-compose.yml
   logging:
     driver: json-file
     options:
       max-size: "10m"
       max-file: "3"
   ```
2. Añadir un stack EFK (Elasticsearch-Fluentd-Kibana) o Loki+Grafana al compose
3. Configurar el log level de la app según el entorno (dev/staging/prod)
4. Crear un script que filtre errores del log y envíe alertas

### Tarea 9: Hardening del Sistema

**Objetivo:** Asegurar los contenedores y la red.

**Pasos:**
1. Verificar que la app NO corre como root (ya está en el Dockerfile)
2. Añadir `read_only: true` a los contenedores donde sea posible
3. Configurar `security_opt: [no-new-privileges:true]`
4. Limitar recursos con `deploy.resources.limits` (CPU y memoria)
5. Crear una red interna separada para la DB (que no sea accesible desde fuera)
6. Restringir el endpoint `/metrics` solo a la red de monitoreo en Nginx
7. Deshabilitar el endpoint `/audit` en producción o protegerlo con auth básica

**Verificación:**
```bash
# Verificar que la API no corre como root
docker exec bookvault-api whoami
# Debe responder: bookvault

# Verificar las redes
docker network ls | grep bookvault
```

---

## FASE 5 — Monitoreo y Observabilidad

### Tarea 10: Stack de Monitoreo con Prometheus + Grafana

**Objetivo:** Ver métricas de la aplicación en dashboards.

**Pasos:**
1. Añadir Prometheus y Grafana al `docker-compose.yml`:
   ```yaml
   prometheus:
     image: prom/prometheus:latest
     volumes:
       - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
     ports:
       - "9090:9090"

   grafana:
     image: grafana/grafana:latest
     ports:
       - "3000:3000"
     environment:
       - GF_SECURITY_ADMIN_PASSWORD=admin
   ```
2. Verificar que Prometheus scrapea las métricas de la API
3. Crear un dashboard en Grafana con:
   - Requests por segundo
   - Latencia (p50, p95, p99)
   - Errores (4xx, 5xx)
   - Status de los healthchecks
4. Configurar alertas en Prometheus (crear `monitoring/alerts.yml`)

**Verificación:**
```bash
# Prometheus targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].health'

# Grafana debe estar en http://localhost:3000 (admin/admin)
```

### Tarea 11: Health Checks y Alerting

**Objetivo:** Detectar problemas automáticamente.

**Pasos:**
1. Hacer ejecutable y probar `scripts/healthcheck.sh`
2. Configurar un cron que corra el healthcheck cada 5 minutos
3. Añadir alertas en Prometheus para:
   - API down por más de 1 minuto
   - Latencia p95 > 500ms
   - Error rate > 5%
4. Conectar las alertas a SNS (LocalStack) con Alertmanager

---

## FASE 6 — Redes y DNS

### Tarea 12: Configuración de Red

**Objetivo:** Segmentar la red correctamente.

**Pasos:**
1. Crear tres redes en Docker Compose:
   - `frontend` — Nginx (la única expuesta)
   - `backend` — API y DB
   - `monitoring` — Prometheus, Grafana
2. La API debe estar en `frontend` y `backend`
3. La DB solo en `backend`
4. Prometheus en `backend` (para scrapear) y `monitoring`
5. Verificar que la DB no es accesible desde la red frontend

**Verificación:**
```bash
# Esto NO debe funcionar (DB aislada)
docker run --rm --network devops-bootcamp_frontend alpine \
  sh -c "apk add postgresql-client && pg_isready -h db -p 5432"
```

---

## FASE 7 — Avanzado (Bonus)

### Tarea 13: Blue-Green Deployment

**Objetivo:** Desplegar sin downtime.

**Pasos:**
1. Crear dos servicios de la API: `api-blue` y `api-green`
2. Configurar Nginx para alternar entre ellos
3. Crear un script `scripts/deploy-blue-green.sh` que:
   - Levante la nueva versión en el color inactivo
   - Corra healthchecks
   - Cambie Nginx al nuevo color
   - Apague la versión vieja

### Tarea 14: Simulación de Incident Response

**Objetivo:** Practicar respondiendo a incidentes.

**Escenarios para simular:**
1. La DB se cae → detectar, alertar, restaurar desde backup
2. El disco se llena → detectar, limpiar, prevenir
3. La API tiene memory leak (simular con `stress`) → detectar, escalar
4. Ataque de fuerza bruta → detectar con logs, bloquear IP en Nginx

---

## Orden Recomendado

| Orden | Tarea | Tema | Dificultad |
|-------|-------|------|------------|
| 1 | Tarea 1 | Docker Basics | ⭐ |
| 2 | Tarea 2 | Reverse Proxy | ⭐⭐ |
| 3 | Tarea 5 | LocalStack + Terraform | ⭐⭐ |
| 4 | Tarea 3 | CI Pipeline | ⭐⭐ |
| 5 | Tarea 7 | Backups | ⭐⭐ |
| 6 | Tarea 9 | Hardening | ⭐⭐⭐ |
| 7 | Tarea 10 | Monitoreo | ⭐⭐⭐ |
| 8 | Tarea 6 | Secretos | ⭐⭐⭐ |
| 9 | Tarea 12 | Redes | ⭐⭐⭐ |
| 10 | Tarea 8 | Logs | ⭐⭐⭐ |
| 11 | Tarea 11 | Alerting | ⭐⭐⭐ |
| 12 | Tarea 4 | CD Pipeline | ⭐⭐⭐⭐ |
| 13 | Tarea 13 | Blue-Green | ⭐⭐⭐⭐ |
| 14 | Tarea 14 | Incident Response | ⭐⭐⭐⭐ |

---

## Cómo Trabajar

1. **Haz una tarea a la vez**, en el orden recomendado
2. **Pregúntame cualquier duda** — estoy aquí para guiarte paso a paso
3. Cuando termines una tarea, dime y la revisamos juntos
4. Si te atascas, dame el error exacto y lo resolvemos

¡Empecemos cuando quieras! Dime "**listo para Tarea 1**" para arrancar.
