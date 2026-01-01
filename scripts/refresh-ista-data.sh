#!/bin/bash
# Script pour rafraîchir les données ISTA NTIC depuis le site officiel
# Usage: ./refresh-ista-data.sh

set -e

echo "🔄 Rafraîchissement des données ISTA NTIC..."
echo "📡 Source: https://sites.google.com/view/ista-ntic-sm/"
echo ""

# Vérifier que le container NTIC2 backend tourne
if ! docker ps | grep -q ntic2_backend; then
    echo "❌ Erreur: Le container ntic2_backend n'est pas démarré"
    echo "   Démarrez-le avec: docker-compose up -d ntic2_backend"
    exit 1
fi

# Exécuter le script de rafraîchissement
docker exec ntic2_backend python3 /app/scripts/refresh_ista_data.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Données rafraîchies avec succès!"
    echo "📊 Vérifiez le résumé: docker exec ntic2_backend cat /app/chroma_db/refresh_summary.json"
else
    echo ""
    echo "❌ Erreur lors du rafraîchissement"
    exit 1
fi
