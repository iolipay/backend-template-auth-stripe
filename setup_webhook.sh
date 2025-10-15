#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Telegram Webhook Setup for Local Development${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Load environment
source .env

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${RED}❌ TELEGRAM_BOT_TOKEN not set in .env${NC}"
    exit 1
fi

echo -e "${YELLOW}📝 Setup Instructions:${NC}"
echo ""
echo "To use Telegram webhooks locally, you need to expose your local server."
echo ""
echo -e "${BLUE}Option 1: ngrok (Recommended)${NC}"
echo "  1. Sign up at: https://dashboard.ngrok.com/signup (free)"
echo "  2. Get your authtoken: https://dashboard.ngrok.com/get-started/your-authtoken"
echo "  3. Run: ngrok config add-authtoken YOUR_TOKEN"
echo "  4. Run this script again"
echo ""
echo -e "${BLUE}Option 2: localtunnel (No signup)${NC}"
echo "  1. Install: npm install -g localtunnel"
echo "  2. Run: lt --port 8000"
echo "  3. Use the URL it gives you"
echo ""
echo -e "${YELLOW}Do you have ngrok configured? (y/n)${NC}"
read -r HAS_NGROK

if [ "$HAS_NGROK" = "y" ] || [ "$HAS_NGROK" = "Y" ]; then
    echo ""
    echo -e "${BLUE}🚀 Starting ngrok...${NC}"

    # Start ngrok in background
    ngrok http 8000 > /tmp/ngrok.log 2>&1 &
    NGROK_PID=$!

    echo "Waiting for ngrok to start..."
    sleep 3

    # Get public URL
    PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null)

    if [ -z "$PUBLIC_URL" ]; then
        echo -e "${RED}❌ Failed to get ngrok URL${NC}"
        kill $NGROK_PID 2>/dev/null
        exit 1
    fi

    echo -e "${GREEN}✅ ngrok started!${NC}"
    echo -e "${GREEN}   Public URL: $PUBLIC_URL${NC}"
    echo ""

    WEBHOOK_URL="$PUBLIC_URL/telegram/webhook"

else
    echo ""
    echo -e "${YELLOW}Enter your public URL (from ngrok/localtunnel):${NC}"
    read -r PUBLIC_URL

    if [ -z "$PUBLIC_URL" ]; then
        echo -e "${RED}❌ No URL provided${NC}"
        exit 1
    fi

    WEBHOOK_URL="$PUBLIC_URL/telegram/webhook"
fi

echo -e "${BLUE}🔗 Setting Telegram webhook...${NC}"
echo "   Webhook URL: $WEBHOOK_URL"

# Set webhook
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
    -d "url=${WEBHOOK_URL}")

SUCCESS=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('ok', False))" 2>/dev/null)

if [ "$SUCCESS" = "True" ]; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Webhook configured successfully!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}📱 Your bot is now ready to receive messages!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Make sure your backend is running: uvicorn app.main:app --reload"
    echo "  2. Run: ./connect_telegram.sh to get your connection link"
    echo "  3. Open the link in Telegram and click 'Start'"
    echo ""

    if [ ! -z "$NGROK_PID" ]; then
        echo -e "${YELLOW}⚠️  Keep ngrok running (PID: $NGROK_PID)${NC}"
        echo "   To stop: kill $NGROK_PID"
        echo ""
    fi

    # Verify webhook
    echo -e "${BLUE}📊 Webhook Info:${NC}"
    curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool | grep -E '(url|pending_update_count)'

else
    echo ""
    echo -e "${RED}❌ Failed to set webhook${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi
