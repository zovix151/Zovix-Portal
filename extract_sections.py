c = open('app.py','r',encoding='utf-8').read()

# 1. Face Lock section - in cinematic engine
idx = c.find('FACE LOCK SECURITY')
start = c.rfind('\n', 0, idx) + 1
# Go back to find the h4 header
h4_idx = c.rfind('h4', idx-300, idx)
start = c.rfind('\n', 0, h4_idx) + 1
# Find next Face Lock section end
face_lock_end = c.find('\n            st.markdown("<hr', idx)
if face_lock_end < 0:
    face_lock_end = c.find('FACE LOCK DISABLED', idx) + 100
segment = c[start:face_lock_end+100]
open('face_lock_full.txt','w',encoding='utf-8').write(segment)
print(f'Face Lock: {len(segment)} chars')

# 2. 2FA section
idx2 = c.find('def show_2fa_modal():')
next_def2 = c.find('\ndef ', idx2 + 30)
if next_def2 < 0: next_def2 = c.find('\n# ===', idx2 + 30)
segment2 = c[idx2:next_def2]
open('twofa_full.txt','w',encoding='utf-8').write(segment2)
print(f'2FA: {len(segment2)} chars')

# 3. Binance section
idx3 = c.find('elif gateway == "binance":')
end3 = c.find('\n    # ===', idx3)
if end3 < 0: end3 = idx3 + 2000
segment3 = c[idx3:end3]
open('binance_full.txt','w',encoding='utf-8').write(segment3)
print(f'Binance: {len(segment3)} chars')

# 4. Also find QR code display in 2FA
qridx = c.find('st.image(.*qr', idx2-500, idx2+500)
print(f'st.image in 2FA area: {qridx >= 0}')

# 5. Find where QR is supposed to be generated/setup
setup_idx = c.find('setup_2fa')
if setup_idx:
    next_def = c.find('\ndef ', setup_idx + 30)
    if next_def < 0: next_def = setup_idx + 2000
    seg = c[setup_idx:next_def]
    open('twofa_setup.txt','w',encoding='utf-8').write(seg)
    print(f'2FA setup: {len(seg)} chars')
else:
    print('No setup_2fa function found')
