# Development Tournament URL

This folder contains example HTML files for testing the Poker Cooler Insurance contract in development.

## Usage

### Option 1: Using Python HTTP Server

1. Navigate to this directory:
   ```bash
   cd dev
   ```

2. Start a simple HTTP server:
   ```bash
   # Python 3
   python -m http.server 8000
   
   # Or Python 2
   python -m SimpleHTTPServer 8000
   ```

3. Use the following URL in your contract calls:
   ```
   http://localhost:8000/tournament_example.html
   ```

### Option 2: Using Node.js HTTP Server

1. Install `http-server` globally (if not already installed):
   ```bash
   npm install -g http-server
   ```

2. Navigate to this directory and start the server:
   ```bash
   cd dev
   http-server -p 8000
   ```

3. Use the following URL in your contract calls:
   ```
   http://localhost:8000/tournament_example.html
   ```

## Tournament Example File

The `tournament_example.html` file contains:

- **Buy-in information**: $100 USD (multiple formats for extraction)
- **Player elimination data**: Three example players with different scenarios:
  - `player123`: Eliminated by cooler (Pocket Aces vs Pocket Kings)
  - `player456`: Eliminated without cooler (weak hand)
  - `player789`: Eliminated by cooler (Flush vs Straight Flush)
- **Tournament status**: Marked as finished

## Customizing for Testing

You can modify `tournament_example.html` to test different scenarios:

1. Change the buy-in amount in the "Tournament Information" section
2. Modify player elimination data to test different cooler scenarios
3. Add or remove players as needed
4. Change tournament status (finished/ongoing)

## Example Contract Call

When calling `purchase_insurance`, use:
```python
tournament_url = "http://localhost:8000/tournament_example.html"
player_id = "player123"  # or "player456", "player789"
```

