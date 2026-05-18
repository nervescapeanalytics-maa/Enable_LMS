"""Feature service layer.

Each function is a thin wrapper around the AI gateway with feature-specific
input shaping. They are the only places where caller code touches gateway
internals; views/serializers call these.
"""
