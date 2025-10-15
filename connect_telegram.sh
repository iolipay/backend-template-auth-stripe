#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}       Telegram Account Connection Helper${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${RED}❌ Backend not running!${NC}"
    echo ""
    echo "Start it with:"
    echo -e "${YELLOW}  source venv/bin/activate${NC}"
    echo -e "${YELLOW}  uvicorn app.main:app --reload${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend is running${NC}"
echo ""

echo -e "${BLUE}📧 Enter your email:${NC}"
read EMAIL

echo -e "${BLUE}🔑 Enter your password:${NC}"
read -s PASSWORD
echo ""

echo -e "${BLUE}🔐 Logging in...${NC}"

# Login and get token
RESPONSE=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$EMAIL&password=$PASSWORD")

TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" == "" ]; then
    echo -e "${RED}❌ Login failed!${NC}"
    echo ""
    ERROR=$(echo "$RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('detail', 'Unknown error'))" 2>/dev/null)
    echo "Error: $ERROR"
    exit 1
fi

echo -e "${GREEN}✅ Logged in successfully${NC}"
echo ""

echo -e "${BLUE}📱 Generating Telegram connection link...${NC}"

# Generate connection link
RESPONSE=$(curl -s -X POST "http://localhost:8000/telegram/connect" \
  -H "Authorization: Bearer $TOKEN")

DEEP_LINK=$(echo "$RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('deep_link', ''))" 2>/dev/null)
BOT_USERNAME=$(echo "$RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('bot_username', ''))" 2>/dev/null)

if [ -z "$DEEP_LINK" ] || [ "$DEEP_LINK" == "" ]; then
    echo -e "${RED}❌ Failed to generate link!${NC}"
    echo ""
    ERROR=$(echo "$RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('detail', 'Unknown error'))" 2>/dev/null)
    echo "Error: $ERROR"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Connection link generated!${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🔗 Your Telegram Connection Link:${NC}"
echo ""
echo -e "${YELLOW}$DEEP_LINK${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📋 Instructions:${NC}"
echo ""
echo "  1. ${GREEN}Copy the link above${NC}"
echo "  2. ${GREEN}Paste it in your browser${NC} or click it"
echo "  3. Telegram will open automatically"
echo "  4. ${GREEN}Click 'Start'${NC} in the bot"
echo "  5. Your account will be linked! 🎉"
echo ""
echo -e "${YELLOW}⏰ Link expires in 1 hour${NC}"
echo ""

# Offer to open in browser
echo -e "${BLUE}Want to open the link now? (y/n)${NC}"
read -r OPEN_NOW

if [ "$OPEN_NOW" = "y" ] || [ "$OPEN_NOW" = "Y" ]; then
    if command -v xdg-open > /dev/null; then
        xdg-open "$DEEP_LINK"
    elif command -v open > /dev/null; then
        open "$DEEP_LINK"
    else
        echo -e "${YELLOW}⚠️  Could not open automatically. Please copy the link manually.${NC}"
    fi
fi

echo ""
echo -e "${BLUE}🔍 To check if connection succeeded:${NC}"
echo -e "${YELLOW}  curl -H \"Authorization: Bearer $TOKEN\" http://localhost:8000/telegram/status${NC}"
echo ""
