   curl -X 'POST' \
   'http://localhost:8002/nodes/' \
   -H 'accept: application/json' \
   -H 'Content-Type: application/json' \
   -d '{
   "site_id": "d6g-000",
   "cpu": 32,
   "ram": 64,
   "mem": 64,
   "iml_endpoint": "10.7.30.11:6000",
   "storage": 64
   }'

   curl -X 'POST' \
   'http://localhost:8002/nodes/' \
   -H 'accept: application/json' \
   -H 'Content-Type: application/json' \
   -d '{
   "site_id": "d6g-001",
   "cpu": 8,
   "ram": 64,
   "mem": 64,
   "iml_endpoint": "10.7.30.11:6000",
   "storage": 2048
   }'

   curl -X 'POST' \
   'http://localhost:8002/nodes/' \
   -H 'accept: application/json' \
   -H 'Content-Type: application/json' \
   -d '{
   "site_id": "d6g-002",
   "cpu": 32,
   "ram": 128,
   "mem": 128,
   "iml_endpoint": "10.8.30.11:6000",
   "storage": 3072
   }'
