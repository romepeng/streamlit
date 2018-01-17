"""A Notebook Object which exposes a print method which can be used to
write objects out to a wbpage."""

import asyncio
import os
import websockets
import threading
from tiny_notebook import delta, protobuf

WEBSOCKET_PORT = 8315
LAUNCH_BROWSER_SCRIPT = \
    'osascript ' \
    './web-client/node_modules/react-dev-utils/openChrome.applescript ' \
    'http://localhost:3000/'
SHUTDOWN_DELAY_SECS = 1.0
THROTTLE_SECONDS = 0.01

class Notebook:
    def __init__(self):
        # Create objects for the server.
        self._server_loop = asyncio.new_event_loop()
        self._server_running = False

        # Here is where we can create text
        self._delta_accumulators = [delta.Accumulator()]
        self._delta_generator = delta.Generator(
            self._delta_accumulators[0].add_delta)

    def __enter__(self):
        # start the webserver
        self._launch_server()

        # launch the webbrowser
        os.system(LAUNCH_BROWSER_SCRIPT)

        # the generator allows the user to create new deltas
        return self._delta_generator

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Shut down the server."""
        # # Display the stack trace if necessary.
        # if exc_type != None:
        #     tb_list = traceback.format_list(traceback.extract_tb(exc_tb))
        #     tb_list.append(f'{exc_type.__name__}: {exc_val}')
        #     self._elts.alert('\n'.join(tb_list))

        # close down the server
        print("About to send out an asynchronous stop.")
        asyncio.run_coroutine_threadsafe(self._async_stop(), self._server_loop)
        print("Sent out the stop")

        # # A small delay to flush anything left.
        # time.sleep(Notebook._OPEN_WEBPAGE_SECS)
        #
        # # Delay server shutdown if we haven't transmitted everything yet
        # if not (self._received_GET and self._transmitted_final_state()):
        #     print(f'Sleeping for {Notebook._FINAL_SHUTDOWN_SECS} '
        #         'seconds to flush all elements.')
        #     time.sleep(Notebook._FINAL_SHUTDOWN_SECS)
        # self._keep_running = False
        # self._httpd.server_close()
        # print('Closed down server.')

    def _launch_server(self):
        """Launches the server and runs an asyncio loop forever."""
        def run_server():
            print("Starting server in separate thread.")
            self._server_running = True
            asyncio.set_event_loop(self._server_loop)
            start_server = websockets.serve(
                self._async_handle_connection, '', WEBSOCKET_PORT)
            try:
                self._server_loop.run_until_complete(start_server)
                print('Starting the server loop...')
                self._server_loop.run_forever()
            finally:
                print('About to close the loop.')
                self._server_loop.close()

        threading.Thread(target=run_server, daemon=True).start()

    async def _async_handle_connection(self, websocket, path):
        """Handles a websocket connection."""
        # Go into an endless loop.
        while self._server_running:
            deltas = self._delta_accumulators[0].get_deltas()
            # print('Found and am sending deltas:', bool(deltas))
            if deltas:
                delta_list = protobuf.DeltaList()
                delta_list.deltas.extend(deltas)
                await websocket.send(delta_list.SerializeToString())

            await asyncio.sleep(THROTTLE_SECONDS)

        print('Naturally finished handle connection.')

    async def _async_stop(self):
        """Stops the server loop."""
        print('Executing an asynchronous stop:', self._server_loop.is_running())
        def stop_server_running():
            self._server_running = False
        self._server_loop.call_later(THROTTLE_SECONDS * 2,
            stop_server_running)
        self._server_loop.call_later(SHUTDOWN_DELAY_SECS,
            self._server_loop.stop)