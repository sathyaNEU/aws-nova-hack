# mcp_server.py
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tools import business_info, policies, menu, reservations, orders, escalation
from data.master_data import load as load_master_data

load_dotenv()

# Load DB-backed data here — this is the process where the tools actually run
load_master_data()

mcp = FastMCP("restaurant-receptionist")

business_info.register(mcp)
policies.register(mcp)
menu.register(mcp)
reservations.register(mcp)
orders.register(mcp)
escalation.register(mcp)

if __name__ == "__main__":
    mcp.run()