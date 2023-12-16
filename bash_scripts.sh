# start neo4j docker container
docker pull neo4j:latest
docker run --name neo4j -p7474:7474 -p7687:7687 -d \
    -e NEO4J_AUTH=neo4j/rag-neo4j \
    -e NEO4JLABS_PLUGINS='["apoc"]' \
    -e NEO4J_apoc_export_file_enabled=true \
    -e NEO4J_apoc_import_file_enabled=true \
    -e NEO4J_apoc_import_file_use__neo4j__config=true \
    neo4j:latest

# start neo4j docker container with bloom
docker pull neo4j:enterprise
docker run --name neo4j-bloom -p7474:7474 -p7687:7687 -p7473:7473 -d \
    -e NEO4J_AUTH=neo4j/rag-neo4j \
    -e NEO4JLABS_PLUGINS='["apoc"]' \
    -e NEO4J_apoc_export_file_enabled=true \
    -e NEO4J_apoc_import_file_enabled=true \
    -e NEO4J_apoc_import_file_use__neo4j__config=true \
    -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
    neo4j:enterprise

# load env variables
set -a && source ../.env && set +a
