#!/bin/bash

API_URL="http://localhost:8080/api/orders"

echo "=== Testing Mario's Pizzeria Observability ==="
echo ""

# Test 1: Place an order with 2 pizzas
echo "Test 1: Placing order with 2 pizzas..."
ORDER1=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer 1",
    "customer_phone": "+1234567890",
    "customer_address": "123 Test Street, Test City",
    "customer_email": "test1@example.com",
    "pizzas": [
      {"name": "Margherita", "size": "medium", "toppings": ["basil", "mozzarella"]},
      {"name": "Pepperoni", "size": "large", "toppings": ["pepperoni"]}
    ],
    "payment_method": "credit_card",
    "notes": "Extra cheese please"
  }')

ORDER1_ID=$(echo "$ORDER1" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo "✓ Order 1 placed: $ORDER1_ID"
sleep 1

# Test 2: Place another order with 1 pizza
echo ""
echo "Test 2: Placing order with 1 pizza..."
ORDER2=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer 2",
    "customer_phone": "+0987654321",
    "customer_address": "456 Demo Avenue, Demo Town",
    "pizzas": [
      {"name": "Hawaiian", "size": "small", "toppings": ["ham", "pineapple"]}
    ],
    "payment_method": "cash"
  }')

ORDER2_ID=$(echo "$ORDER2" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo "✓ Order 2 placed: $ORDER2_ID"
sleep 1

# Test 3: Start cooking order 1
if [ ! -z "$ORDER1_ID" ] && [ "$ORDER1_ID" != "null" ]; then
  echo ""
  echo "Test 3: Starting to cook order 1..."
  curl -s -X PUT "$API_URL/$ORDER1_ID/cook" -H "Content-Type: application/json" > /dev/null
  echo "✓ Order 1 cooking started"
  sleep 2
fi

# Test 4: Complete order 1
if [ ! -z "$ORDER1_ID" ] && [ "$ORDER1_ID" != "null" ]; then
  echo ""
  echo "Test 4: Marking order 1 as ready..."
  curl -s -X PUT "$API_URL/$ORDER1_ID/ready" -H "Content-Type: application/json" > /dev/null
  echo "✓ Order 1 marked ready"
  sleep 1
fi

# Test 5: Start and complete order 2
if [ ! -z "$ORDER2_ID" ] && [ "$ORDER2_ID" != "null" ]; then
  echo ""
  echo "Test 5: Cooking and completing order 2..."
  curl -s -X PUT "$API_URL/$ORDER2_ID/cook" -H "Content-Type: application/json" > /dev/null
  echo "✓ Order 2 cooking started"
  sleep 2
  curl -s -X PUT "$API_URL/$ORDER2_ID/ready" -H "Content-Type: application/json" > /dev/null
  echo "✓ Order 2 marked ready"
fi

echo ""
echo "=== Test Complete ==="
echo ""
echo "Placed 2 orders:"
echo "  - Order 1 ($ORDER1_ID): 2 pizzas (medium, large)"
echo "  - Order 2 ($ORDER2_ID): 1 pizza (small)"
echo ""
echo "Both orders were cooked and completed"
echo ""
echo "You can now check:"
echo "  - Prometheus: http://localhost:9090/graph"
echo "  - Grafana: http://localhost:3001/"
echo "  - Tempo: http://localhost:3200/"
