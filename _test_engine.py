import sys
sys.stdout.reconfigure(encoding="utf-8")

# Test import of validate_and_deduct_tokens
try:
    from deepinfra_engine import validate_and_deduct_tokens
    print("RESULT:", validate_and_deduct_tokens("Cinematic Engine", "HD"))
except Exception as e:
    print("IMPORT/EXEC ERROR:", repr(e))

# Test production_engine import
try:
    import production_engine
    print("production_engine import OK")
except Exception as e:
    print("production_engine IMPORT ERROR:", repr(e))

# Test creating DeepInfraFaceEngine
try:
    from deepinfra_engine import DeepInfraFaceEngine
    engine = DeepInfraFaceEngine()
    print("Engine available:", engine.is_available())
except Exception as e:
    print("DeepInfraFaceEngine ERROR:", repr(e))
