#!/bin/bash
set -e

echo "📦 Installation des dépendances manquantes..."
pip3 install sounddevice pynput

echo ""
echo "✅ Prêt !"
echo ""
echo "📋 Étape obligatoire — Permission Accessibilité :"
echo "   System Settings → Privacy & Security → Accessibility"
echo "   → Ajoute ton terminal (Terminal / iTerm / Warp)"
echo ""
echo "🚀 Lance avec : ./start.sh"
