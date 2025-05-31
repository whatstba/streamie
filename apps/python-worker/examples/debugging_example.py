"""
Example: How to use Python's built-in debugger (pdb)
"""

# Example 1: Using the old-style pdb
def analyze_track_with_pdb(filepath):
    # Add this line where you want to debug
    import pdb; pdb.set_trace()
    
    # Your code continues here
    print(f"Analyzing: {filepath}")
    return {"result": "success"}


# Example 2: Using Python 3.7+ breakpoint()
def analyze_track_with_breakpoint(filepath):
    # This is cleaner and more modern
    breakpoint()  # Execution will pause here
    
    # Your code continues here
    print(f"Analyzing: {filepath}")
    return {"result": "success"}


# When the debugger stops, you can use these commands:
# n - Next line
# s - Step into function
# c - Continue execution
# l - List current code
# p variable - Print variable value
# pp variable - Pretty print variable
# h - Help (show all commands)

# To add a conditional breakpoint:
def process_multiple_tracks(tracks):
    for i, track in enumerate(tracks):
        # Only break when i == 5
        if i == 5:
            breakpoint()
        
        print(f"Processing track {i}: {track}")


# To debug in your FastAPI endpoints, just add:
# breakpoint()
# anywhere in your endpoint function 