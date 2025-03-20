// renderer.js

document.addEventListener('DOMContentLoaded', () => {
    const TRADE_API_URL = 'http://127.0.0.1:5000/trades';
    const OPTION_API_BASE = 'http://127.0.0.1:5000/option';
    const TOOLBAR_API_BASE = 'http://127.0.0.1:5000/toolbar';
  
    async function fetchTrades() {
        try {
            logDebug('Fetching trades from backend...');
            const response = await fetch(TRADE_API_URL);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const trades = await response.json();
            logDebug(`Fetched ${trades.length} trades successfully.`);
            updateTable(trades);
        } catch (error) {
            logDebug(`Error fetching trades: ${error.message}`);
            displayErrorMessage('Unable to fetch trades. Please check the backend and API URL.');
        }
    }
  
    function updateTable(trades) {
        const tableBody = document.querySelector('.trade-table tbody');
        if (!tableBody) {
            console.error("Table body element not found! Check your HTML structure.");
            return;
        }
        tableBody.innerHTML = ''; // Clear existing rows
        trades.forEach(trade => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${trade['source'] || ''}</td>
                <td>${trade['id'] || ''}</td>
                <td>${trade['account-number'] || ''}</td>
                <td>${trade['action'] || ''}</td>
                <td>${trade['quantity'] || ''}</td>
                <td>${trade['symbol'] || ''}</td>
                <td>${trade['price'] || ''}</td>
                <td>${trade['commission'] || ''}</td>
                <td>${trade['currency'] || ''}</td>
                <td>${trade['exec-id'] || ''}</td>
                <td>${trade['exchange'] || ''}</td>
                <td>${trade['executed-at'] || ''}</td>
                <td>${trade['instrument-type'] || ''}</td>
                <td>${trade['description'] || ''}</td>
                <td>${trade['destination-venue'] || ''}</td>
                <td>${trade['ext-exchange-order-number'] || ''}</td>
                <td>${trade['ext-exec-id'] || ''}</td>
                <td>${trade['ext-global-order-number'] || ''}</td>
                <td>${trade['ext-group-fill-id'] || ''}</td>
                <td>${trade['ext-group-id'] || ''}</td>
                <td>${trade['is-estimated-fee'] || ''}</td>
                <td>${trade['leg-count'] || ''}</td>
                <td>${trade['net-value'] || ''}</td>
                <td>${trade['net-value-effect'] || ''}</td>
                <td>${trade['order-id'] || ''}</td>
                <td>${trade['transaction-date'] || ''}</td>
                <td>${trade['transaction-sub-type'] || ''}</td>
                <td>${trade['transaction-type'] || ''}</td>
                <td>${trade['underlying-symbol'] || ''}</td>
                <td>${trade['value'] || ''}</td>
                <td>${trade['value-effect'] || ''}</td>
                <td>${trade['clearing-fees'] || ''}</td>
                <td>${trade['clearing-fees-effect'] || ''}</td>
                <td>${trade['commission-effect'] || ''}</td>
            `;
            tableBody.appendChild(row);
        });
        logDebug(`Updated table with ${trades.length} rows.`);
    }
  
    function displayErrorMessage(message) {
        const tableBody = document.querySelector('.trade-table tbody');
        tableBody.innerHTML = `<tr><td colspan="38" style="color: red; text-align: center;">${message}</td></tr>`;
        logDebug(message);
    }
  
    function logDebug(message) {
        const debugPanel = document.getElementById('debug-panel');
        const timestamp = new Date().toLocaleTimeString();
        if (debugPanel) {
            debugPanel.innerHTML += `<div>[${timestamp}] ${message}</div>`;
            debugPanel.scrollTop = debugPanel.scrollHeight;
        }
        console.log(`[${timestamp}] ${message}`);
    }

    // Update the status bar message
    function updateStatusBar(message, isError = false) {
        const statusMessage = document.getElementById('status-message');
        const statusTimestamp = document.getElementById('status-timestamp');
        const timestamp = new Date().toLocaleTimeString();
        
        if (statusMessage) {
            statusMessage.innerText = message;
            if (isError) {
                statusMessage.style.color = '#e74c3c';
            } else {
                statusMessage.style.color = 'white';
            }
        }
        
        if (statusTimestamp) {
            statusTimestamp.innerText = timestamp;
        }
        
        // Also update the toolbar status
        const toolbarStatus = document.getElementById('toolbar-status');
        if (toolbarStatus) {
            toolbarStatus.innerText = message;
        }
    }

    // Function to initialize toolbar buttons
    function initToolbar() {
        // Play button
        document.getElementById('play-btn').addEventListener('click', async () => {
            try {
                updateStatusBar('Starting system...');
                const response = await fetch(`${TOOLBAR_API_BASE}/play`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                
                const data = await response.json();
                updateStatusBar(data.message);
                logDebug(`Toolbar action: ${data.message}`);
            } catch (error) {
                updateStatusBar(`Error: ${error.message}`, true);
                logDebug(`Toolbar action error: ${error.message}`);
            }
        });
        
        // Pause button
        document.getElementById('pause-btn').addEventListener('click', async () => {
            try {
                updateStatusBar('Pausing system...');
                const response = await fetch(`${TOOLBAR_API_BASE}/pause`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                
                const data = await response.json();
                updateStatusBar(data.message);
                logDebug(`Toolbar action: ${data.message}`);
            } catch (error) {
                updateStatusBar(`Error: ${error.message}`, true);
                logDebug(`Toolbar action error: ${error.message}`);
            }
        });
        
        // Stop button
        document.getElementById('stop-btn').addEventListener('click', async () => {
            try {
                updateStatusBar('Stopping system...');
                const response = await fetch(`${TOOLBAR_API_BASE}/stop`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                
                const data = await response.json();
                updateStatusBar(data.message);
                logDebug(`Toolbar action: ${data.message}`);
            } catch (error) {
                updateStatusBar(`Error: ${error.message}`, true);
                logDebug(`Toolbar action error: ${error.message}`);
            }
        });
        
        logDebug('Toolbar initialized.');
    }

    // Options Workflow Functions
    function initOptionsWorkflow() {
        // Attach event listeners for options buttons
        document.getElementById('init-option-btn').addEventListener('click', () => {
            fetch(`${OPTION_API_BASE}/init`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('init-option-result').innerText =
                        data.error ? `Error: ${data.error}` : `Initialized at ${data.timestamp}`;
                })
                .catch(err => {
                    document.getElementById('init-option-result').innerText = `Error: ${err.message}`;
                });
        });

        document.getElementById('get-total-pnl-btn').addEventListener('click', () => {
            fetch(`${OPTION_API_BASE}/get_total_pnl_tos`)
                .then(response => response.json())
                .then(data => updateResult('get-total-pnl-result', data))
                .catch(err => updateResult('get-total-pnl-result', { error: err.message }));
        });

        document.getElementById('get-total-exposure-btn').addEventListener('click', () => {
            fetch(`${OPTION_API_BASE}/get_total_exposure`)
                .then(response => response.json())
                .then(data => updateResult('get-total-exposure-result', data))
                .catch(err => updateResult('get-total-exposure-result', { error: err.message }));
        });

        document.getElementById('get-opt-exposure-btn').addEventListener('click', () => {
            fetch(`${OPTION_API_BASE}/get_opt_exposure`)
                .then(response => response.json())
                .then(data => updateResult('get-opt-exposure-result', data))
                .catch(err => updateResult('get-opt-exposure-result', { error: err.message }));
        });

        document.getElementById('get-hedge-pnl-btn').addEventListener('click', () => {
            fetch(`${OPTION_API_BASE}/get_hedge_pnl_tos`)
                .then(response => response.json())
                .then(data => updateResult('get-hedge-pnl-result', data))
                .catch(err => updateResult('get-hedge-pnl-result', { error: err.message }));
        });

        document.getElementById('get-option-pnl-btn').addEventListener('click', () => {
            fetch(`${OPTION_API_BASE}/get_option_pnl_tos`)
                .then(response => response.json())
                .then(data => updateResult('get-option-pnl-result', data))
                .catch(err => updateResult('get-option-pnl-result', { error: err.message }));
        });

        // Interval processing for options workflow:
        let intervalID = null;
        document.getElementById('start-interval-btn').addEventListener('click', () => {
            const intervalSeconds = parseInt(document.getElementById('interval-input').value, 10);
            if (isNaN(intervalSeconds) || intervalSeconds < 1) {
                alert('Please enter a valid interval (in seconds).');
                return;
            }
            // Clear any existing interval:
            if (intervalID) clearInterval(intervalID);
            intervalID = setInterval(() => {
                Promise.all([
                    fetch(`${OPTION_API_BASE}/get_total_exposure`).then(r => r.json()),
                    fetch(`${OPTION_API_BASE}/get_total_pnl_tos`).then(r => r.json()),
                    fetch(`${OPTION_API_BASE}/push_hedge_trades`, { method: 'POST' }).then(r => r.json())
                ])
                    .then(results => {
                        const [totalExposure, totalPnl, hedgeTrades] = results;
                        const timestamp = new Date().toLocaleTimeString();
                        document.getElementById('interval-status').innerText =
                            `At ${timestamp}: Total Exposure = ${totalExposure.result}, Total PnL = ${totalPnl.result}, Hedge trades: ${hedgeTrades.result || hedgeTrades.error}`;
                    })
                    .catch(error => {
                        document.getElementById('interval-status').innerText = `Error: ${error.message}`;
                    });
            }, intervalSeconds * 1000);
        });

        document.getElementById('stop-interval-btn').addEventListener('click', () => {
            if (intervalID) {
                clearInterval(intervalID);
                intervalID = null;
                document.getElementById('interval-status').innerText = "Interval process stopped.";
            }
        });
    }

    // Helper for options result updates
    function updateResult(elementId, data) {
        const el = document.getElementById(elementId);
        if (el) {
            if (data.error) {
                el.innerText = `Error: ${data.error}`;
            } else {
                el.innerText = `Result: ${data.result} (Last executed: ${data.timestamp})`;
            }
        }
    }

    // Initialize trade fetching with a delay
    setTimeout(() => {
        fetchTrades();
        // Then fetch every 5 seconds
        setInterval(fetchTrades, 5000);
    }, 3000);

    // Initialize toolbar and status bar
    updateStatusBar('Application initializing...');
    initToolbar();

    // Initialize options workflow independently
    setTimeout(() => {
        initOptionsWorkflow();
        updateStatusBar('Application ready');
    }, 3000);
});
  