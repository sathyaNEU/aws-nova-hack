from mcp.server.fastmcp import FastMCP
from tools import business_info, policies, menu, reservations, orders, escalation, transfer
from data.master_data import load as load_master_data
import os
load_master_data()

mcp = FastMCP("restaurant-receptionist")

business_info.register(mcp)
policies.register(mcp)
menu.register(mcp)
reservations.register(mcp)
orders.register(mcp)
escalation.register(mcp)
transfer.register(mcp)
if __name__ == "__main__":
    mcp.run()