SC_CATALOG=localhost:8001
curl -X 'POST' "http://$SC_CATALOG/catalog/" -F "file=@apps.nf.yaml"
curl -X 'POST' "http://$SC_CATALOG/catalog/" -F "file=@apps.sg.yml"
curl -X 'POST' "http://$SC_CATALOG/catalog/" -F "file=@demo1_nsd.sg.yml"
