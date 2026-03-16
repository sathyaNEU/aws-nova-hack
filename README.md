# Nova Dine - AI Voice Receptionist

> Built for the **AWS Hackathon** · Powered by Amazon Nova Sonic + Twilio

Nova Dine is a fully AI-powered phone receptionist for a restaurant. Callers speak naturally to make reservations, place takeout orders, and ask about the menu - no hold music, no phone trees. A parallel **Slack agent** lets staff manage store operations (hours, inventory, and policies) without leaving their chat workspace.

---

## Architecture

![Architecture Diagram](https://raw.githubusercontent.com/sathyaNEU/aws-nova-hack/refs/heads/master/public/assets/sonicserve_arch.png)

The system is split into two independent paths:

**Voice path:** Twilio receives an inbound call and opens a WebSocket media stream to the FastAPI server. Audio is relayed to Amazon Nova Sonic (Bedrock) which handles bidirectional streaming with barge-in detection. Nova Sonic calls tools via an MCP server (FastMCP) to handle reservations, orders, menu lookups, escalations, and call transfers.

**Slack path:** A Strands agent powered by Amazon Nova Pro listens for staff mentions and DMs in Slack. It calls its own set of tools directly (no MCP) to update business hours, manage Square inventory, and edit policies stored in PostgreSQL.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Voice AI | Amazon Nova Sonic (Bedrock) |
| Slack AI | Amazon Nova Pro (Bedrock) via Strands |
| Telephony | Twilio, PSTN + WebSocket media streams |
| Tool protocol | MCP via FastMCP |
| POS integration | Square Orders and Catalog API |
| Database | PostgreSQL (RDS) |
| API server | FastAPI + Uvicorn |
| Deployment | Docker, AWS ECR, AWS ECS |
| Local tunneling | ngrok |

---

## Repository Structure

```
.
├── app.py                          # FastAPI entrypoint, Twilio WebSocket + Slack action handler
├── nova_sonic.py                   # Nova Sonic session, audio relay, barge-in logic
├── mcp_client.py                   # MCP client wrapper (tool discovery + invocation)
├── mcp_server.py                   # MCP server, registers all voice tools
├── Dockerfile                      # Voice server container
├── docker-compose.yml              # Voice server compose
├── requirements.txt
│
├── tools/                          # MCP tools (voice path only)
│   ├── business_info.py            # get_business_hours, get_location, get_parking_info
│   ├── escalation.py               # escalate_to_manager (Slack Block Kit)
│   ├── menu.py                     # get_menu, search_menu
│   ├── orders.py                   # place_order, get_order_status
│   ├── policies.py                 # get_policy
│   ├── reservations.py             # create_reservation, cancel_reservation
│   └── transfer.py                 # transfer_call (Twilio)
│
├── data/
│   ├── master_data.py              # In-memory cache, loaded from DB + Square at startup
│   ├── policies_data.py            # Fallback static policies
│   ├── restaurant.py               # Static restaurant + parking info
│   ├── square_payload.json         # Square catalog seed payload
│   └── seed/
│       ├── business_hours.sql      # Creates and seeds business_hours table
│       ├── square_batch_insert.py
│       ├── square_batch_delete.py
│       └── clover-bootstrap.py
│
├── utils/
│   ├── audio.py                    # u-law / PCM resampling (Twilio / Nova Sonic)
│   ├── pos/
│   │   ├── base.py                 # POSProvider abstract interface
│   │   ├── factory.py              # Returns Square or Clover provider
│   │   ├── square.py               # Square Orders + Catalog API
│   │   └── clover.py               # Clover Orders API
│   ├── rds/
│   │   ├── business_hours/core.py
│   │   ├── policies/core.py
│   │   └── reservations/core.py
│   └── slack/
│       └── actions.py              # Signature verification + Block Kit action handlers
│
├── public/
│   └── assets/
│       └── sonicserve_arch.png
│
└── slack-agent/                    # Independent Slack operations agent
    ├── slack_app.py                # Slack Bolt app, mentions + DMs
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    ├── db/
    │   └── schema.sql              # Creates business_hours + policy_information tables
    └── agent/
        ├── agent.py                # Strands agent, Nova Pro, tool registration
        └── tools/
            ├── business_hours.py   # get_business_hours, update_business_hours
            ├── square_inventory.py # mark_item_sold_out, mark_item_back_in_stock
            └── policy.py           # list_policies, get_policy, update_policy
```

---

## Prerequisites

- Python 3.12+
- Docker
- AWS account with Bedrock access: Nova Sonic (`amazon.nova-2-sonic-v1:0`) and Nova Pro (`us.amazon.nova-pro-v1:0`) enabled in `us-east-1`
- Twilio account with a phone number
- Square developer account (sandbox or production)
- PostgreSQL database (local or RDS)
- Slack app with bot token and signing secret
- ngrok (local development only)

---

## Environment Variables

Create a `.env` file in the project root. The same file is used by both the voice server and the Slack agent; copy it into `slack-agent/` as well, or mount it via Docker.

```dotenv
# AWS credentials
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1

# Square POS
SQUARE_ACCESS_TOKEN=
SQUARE_LOCATION_ID=
SQUARE_ENV=sandbox                  # sandbox or production

# Clover POS (optional alternative to Square)
CLOVER_API_TOKEN=
CLOVER_MERCHANT_ID=

# Slack
SLACK_BOT_TOKEN=                    # xoxb- bot token
SLACK_SIGNING_SECRET=               # used to verify incoming Slack requests
SLACK_ESCALATION_CHANNEL=#manager-alerts
SLACK_RESERVATION_CHANNEL=#reservations

# PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TRANSFER_PHONE_NUMBER=              # E.164 format, e.g. +16175550100
```

---

## Database Setup

Run the seed SQL once against your PostgreSQL instance to create the required tables and insert default data:

```bash
psql $DATABASE_URL -f data/seed/business_hours.sql
psql $DATABASE_URL -f slack-agent/db/schema.sql
```

To load the menu catalog into Square sandbox:

```bash
pip install squareup python-dotenv
python data/seed/square_batch_insert.py
```

---

## Local Development

### Voice server

```bash
# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn app:app --reload --port 3000

# In a second terminal, open a public tunnel
ngrok http 3000
```

Copy the ngrok HTTPS URL and set it as your Twilio phone number's **Voice webhook**:

```
https://<your-ngrok-id>.ngrok.io/incoming-call
```

Twilio will POST to `/incoming-call` on each inbound call and upgrade to a WebSocket at `/media-stream`.

### Slack agent

```bash
cd slack-agent

pip install -r requirements.txt

python slack_app.py
```

The Slack agent uses Socket Mode, so no public URL or ngrok tunnel is needed. Make sure **Socket Mode** is enabled in your Slack app settings and `SLACK_APP_TOKEN` is present in your `.env`.

---

## Call Flow

```mermaid
sequenceDiagram
    participant Caller
    participant Twilio
    participant FastAPI
    participant NovaSonic
    participant MCP

    Caller->>Twilio: Inbound call
    Twilio->>FastAPI: POST /incoming-call
    FastAPI-->>Twilio: TwiML <Stream url="wss://.../media-stream"/>
    Twilio->>FastAPI: WebSocket connect
    FastAPI->>NovaSonic: Start Bedrock session
    NovaSonic-->>Caller: "Thank you for calling Nova Dine..."
    loop Conversation
        Caller->>FastAPI: Audio (u-law 8kHz)
        FastAPI->>NovaSonic: PCM 16kHz
        NovaSonic->>MCP: Tool call (e.g. create_reservation)
        MCP-->>NovaSonic: Tool result
        NovaSonic-->>FastAPI: PCM 24kHz
        FastAPI-->>Twilio: Audio (u-law 8kHz)
        Twilio-->>Caller: Speech
    end
```

---

## Production Deployment (AWS ECS)

The voice server is containerized and deployed to ECS via ECR. The Twilio webhook is pointed at the ECS service URL instead of ngrok.

### 1. Authenticate Docker with ECR

```bash
aws ecr get-login-password --region us-east-1 --profile dev-pers \
  | docker login --username AWS --password-stdin \
    374834463497.dkr.ecr.us-east-1.amazonaws.com
```

### 2. Build and push the image

```bash
docker build -t sonic-serve .

docker tag sonic-serve:latest \
  374834463497.dkr.ecr.us-east-1.amazonaws.com/aws-nova-hack:latest

docker push \
  374834463497.dkr.ecr.us-east-1.amazonaws.com/aws-nova-hack:latest
```

### 3. Force a new deployment

```bash
aws ecs update-service \
  --cluster default \
  --service aws-nova-hack-dd04 \
  --force-new-deployment \
  --region us-east-1 \
  --profile dev-pers
```

### 4. Point Twilio to your ECS service URL

Once the ECS task is running, update the Twilio voice webhook to your service's public URL:

```
https://<your-ecs-url>/incoming-call
```

This replaces the ngrok tunnel used in local development with no other changes required.

### Docker Compose (local full-stack)

```bash
docker-compose up --build
```

This starts the voice server on port 3000. The Slack agent has its own compose file in `slack-agent/`:

```bash
cd slack-agent
docker-compose up --build
```

---

## Slack Agent Usage

Invite the bot to any channel or DM it directly. Example commands:

| Intent | Message |
|---|---|
| View all hours | `what are our hours?` |
| Close for a day | `we're closed this Sunday` |
| Change open time | `Monday opens at 8am` |
| Mark item sold out | `the BBQ Bacon Burger ran out` |
| Restock an item | `BBQ Bacon Burger is back` |
| List policies | `show me all policies` |
| Update a policy | `update the dress_code policy to: smart casual only` |

---

## Key Design Decisions

**MCP for the voice path:** Tools are registered as MCP-compliant specs so Nova Sonic can invoke them natively via Bedrock's tool-use protocol. This keeps `nova_sonic.py` decoupled from any specific business logic.

**Strands for the Slack path:** The Slack agent is a standalone Strands agent with its own tools. It does not share the MCP server; its tools call PostgreSQL and Square directly, which keeps latency low for synchronous Slack interactions.

**Barge-in handling:** When Nova Sonic detects the caller speaking mid-response, the server clears Twilio's audio playback buffer, increments a generation ID to drop stale audio chunks, and reopens the audio channel without dropping the WebSocket connection.

**master_data cache:** Policies, business hours, and the Square menu are fetched once at startup into an in-memory dict. This avoids repeated DB and API calls on every tool invocation during a call.

---
