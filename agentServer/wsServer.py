import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set
import websockets
from websockets.server import WebSocketServerProtocol
from investigation import run_full_investigation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_COMPANY_NAME = "ExxonMobil"
DEFAULT_BILL_NAME = "hr2307-117"

class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=8766):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.active_investigations: Dict[str, asyncio.Task] = {}
        
    async def register_client(self, websocket: WebSocketServerProtocol):
        """Register a new client connection"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send welcome message
        await self.send_to_client(websocket, {
            "type": "connection_established",
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to AutoGen WebSocket server"
        })
    
    async def unregister_client(self, websocket: WebSocketServerProtocol):
        """Unregister a client connection"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def send_to_client(self, websocket: WebSocketServerProtocol, message: dict):
        """Send message to a specific client"""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            await self.unregister_client(websocket)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return
            
        # Add timestamp to message
        message["timestamp"] = datetime.now().isoformat()
        
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            await self.unregister_client(client)
    
    async def handle_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle incoming messages from clients"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "start_investigation":
                await self.start_investigation(websocket, data)
            elif message_type == "start_full_investigation":
                await self.start_full_investigation(websocket, data)
            elif message_type == "stop_investigation":
                await self.stop_investigation(websocket, data)
            elif message_type == "ping":
                await self.send_to_client(websocket, {"type": "pong"})
            else:
                await self.send_to_client(websocket, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
                
        except json.JSONDecodeError:
            await self.send_to_client(websocket, {
                "type": "error", 
                "message": "Invalid JSON format"
            })
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_to_client(websocket, {
                "type": "error",
                "message": f"Server error: {str(e)}"
            })
    
    async def start_investigation(self, websocket: WebSocketServerProtocol, data: dict):
        """Start a new AutoGen investigation"""
        session_id = data.get("sessionId", f"session_{datetime.now().timestamp()}")
        company_name = data.get("company", DEFAULT_COMPANY_NAME)
        bill = data.get("bill", DEFAULT_BILL_NAME)
        
        # Check if investigation is already running
        if session_id in self.active_investigations:
            await self.send_to_client(websocket, {
                "type": "error",
                "message": f"Investigation {session_id} is already running"
            })
            return
        
        logger.info(f"Starting investigation: {session_id} for {company_name} - {bill}")
        
        # Create callback function for this session
        async def websocket_callback(event):
            """Callback function to send AutoGen events to clients"""
            event["sessionId"] = session_id
            await self.broadcast_to_all(event)
        
        # Start the investigation task (using full 6-agent investigation)
        try:
            task = asyncio.create_task(
                run_full_investigation(company_name, bill, websocket_callback)
            )
            self.active_investigations[session_id] = task
            
            # Send confirmation
            await self.send_to_client(websocket, {
                "type": "investigation_started",
                "sessionId": session_id,
                "company": company_name,
                "bill": bill,
                "agents": ["committee_specialist", "bill_specialist", "actions_specialist", "amendment_specialist", "congress_member_specialist", "orchestrator"]
            })
            
            # Wait for investigation to complete
            await task
            
            # Clean up
            if session_id in self.active_investigations:
                del self.active_investigations[session_id]
                
        except Exception as e:
            logger.error(f"Error in investigation {session_id}: {e}")
            await self.broadcast_to_all({
                "type": "investigation_error",
                "sessionId": session_id,
                "error": str(e)
            })
            
            # Clean up on error
            if session_id in self.active_investigations:
                del self.active_investigations[session_id]
    
    async def start_full_investigation(self, websocket: WebSocketServerProtocol, data: dict):
        """Start a full multi-agent AutoGen investigation"""
        session_id = data.get("sessionId", f"full_session_{datetime.now().timestamp()}")
        company_name = data.get("company", DEFAULT_COMPANY_NAME)
        bill = data.get("bill", DEFAULT_BILL_NAME)
        
        # Check if investigation is already running
        if session_id in self.active_investigations:
            await self.send_to_client(websocket, {
                "type": "error",
                "message": f"Investigation {session_id} is already running"
            })
            return
        
        logger.info(f"Starting FULL investigation: {session_id} for {company_name} - {bill}")
        
        # Create callback function for this session
        async def websocket_callback(event):
            """Callback function to send AutoGen events to clients"""
            event["sessionId"] = session_id
            await self.broadcast_to_all(event)
        
        # Start the full investigation task
        try:
            task = asyncio.create_task(
                run_full_investigation(company_name, bill, websocket_callback)
            )
            self.active_investigations[session_id] = task
            
            # Send confirmation
            await self.send_to_client(websocket, {
                "type": "full_investigation_started",
                "sessionId": session_id,
                "company": company_name,
                "bill": bill,
                "agents": ["committee_specialist", "bill_specialist", "actions_specialist", "amendment_specialist", "congress_member_specialist", "orchestrator"]
            })
            
            # Wait for investigation to complete
            await task
            
            # Clean up
            if session_id in self.active_investigations:
                del self.active_investigations[session_id]
                
        except Exception as e:
            logger.error(f"Error in full investigation {session_id}: {e}")
            await self.broadcast_to_all({
                "type": "investigation_error",
                "sessionId": session_id,
                "error": str(e)
            })
            
            # Clean up on error
            if session_id in self.active_investigations:
                del self.active_investigations[session_id]
    
    async def stop_investigation(self, websocket: WebSocketServerProtocol, data: dict):
        """Stop a running investigation"""
        session_id = data.get("sessionId")
        
        if not session_id:
            await self.send_to_client(websocket, {
                "type": "error",
                "message": "sessionId is required"
            })
            return
        
        if session_id not in self.active_investigations:
            await self.send_to_client(websocket, {
                "type": "error", 
                "message": f"No active investigation found for session {session_id}"
            })
            return
        
        # Cancel the investigation task
        task = self.active_investigations[session_id]
        task.cancel()
        del self.active_investigations[session_id]
        
        await self.broadcast_to_all({
            "type": "investigation_stopped",
            "sessionId": session_id
        })
        
        logger.info(f"Investigation {session_id} stopped")
    
    async def handle_client(self, websocket: WebSocketServerProtocol):
        """Handle a client connection"""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Error in client handler: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        
        logger.info("WebSocket server started successfully")
        return server

async def main():
    """Main function to run the WebSocket server"""
    server_instance = WebSocketServer()
    
    # Start the server
    server = await server_instance.start_server()
    
    try:
        # Keep the server running
        await server.wait_closed()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    finally:
        # Clean up any active investigations
        for session_id, task in server_instance.active_investigations.items():
            task.cancel()
            logger.info(f"Cancelled investigation: {session_id}")
        
        server.close()
        await server.wait_closed()
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())