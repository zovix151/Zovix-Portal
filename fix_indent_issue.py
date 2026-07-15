c = open('app.py','r',encoding='utf-8').read()

old = '''        return result
     
        try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from deepface import DeepFace
            import tensorflow as tf
            tf.get_logger().setLevel("ERROR")
            os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
            
            analysis = DeepFace.analyze(img_path=image_path, actions=actions, enforce_detection=False, prog_bar=False)'''

new = '''        return result
    
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from deepface import DeepFace
            import tensorflow as tf
            tf.get_logger().setLevel("ERROR")
            os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
            
            analysis = DeepFace.analyze(img_path=image_path, actions=actions, enforce_detection=False, prog_bar=False)'''

count = c.count(old)
print(f'Found {count} occurrence(s)')
if count > 0:
    c = c.replace(old, new)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(c)
    try:
        compile(c, 'app.py', 'exec')
        print('Syntax: OK')
    except SyntaxError as e:
        print(f'Syntax Error: {e}')
else:
    print('Not found')
    idx = c.find('        return result')
    idx2 = c.find('        return result', idx+10)
    print(f'First at {idx}, Second at {idx2}')
    if idx2 > 0:
        print(f'Second context: {repr(c[idx2:idx2+250])}')
