# Tailnet -> LAN TCP forwarder for the Klipper printer (Fluidd + Moonraker).
# Raw TCP, so websockets pass through untouched. Binds only to the tailscale IP.
import asyncio
BIND = "TAILNET_IP"
PRINTER = "PRINTER_LAN_IP"
ROUTES = {8090: 80, 7125: 7125}   # local port -> printer port

async def pipe(r, w):
    try:
        while data := await r.read(65536):
            w.write(data); await w.drain()
    except Exception:
        pass
    finally:
        w.close()

def handler(dport):
    async def h(cr, cw):
        try:
            pr, pw = await asyncio.open_connection(PRINTER, dport)
        except Exception:
            cw.close(); return
        await asyncio.gather(pipe(cr, pw), pipe(pr, cw))
    return h

async def main():
    servers = [await asyncio.start_server(handler(d), BIND, l) for l, d in ROUTES.items()]
    await asyncio.gather(*(s.serve_forever() for s in servers))

asyncio.run(main())
