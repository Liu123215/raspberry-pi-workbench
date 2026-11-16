#!/usr/bin/env python3
"""Personal Raspberry Pi workbench; stdlib only. Run with python3 backend.py."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs, quote, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path
from http.cookies import SimpleCookie
import copy
import hmac
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
import fan_control
import update_service
# Compatibility with the original 1.0 updater, which downloads only four files.
# Its first update to 2.0 may not include these two modules; use the exact
# embedded release copies until the 2.0 updater installs the standalone files.
import base64
import importlib
import sys
import types
import zlib
_EMBEDDED_MODULES = {
    'workbench_extra': 'c-qBSTW{RP6@J&Rn5qvXn-#V4t+oIaNUh|dXey)5rGO#`Tyj>+ESJL!hq_b{5W{tB7*^sUc2ZYrBR6&%w6)weshz}8{b$5o>8XFA=gbVbBzLuv(*l)Y>|D?Fn{(m#`1nN@#)3P3NIeoT*9l0|4`_|Vf^laF2b3@SE+tOrk%+BOPFO^_BYe1MkB^U!`JISyK^jg>&z;F;EY3!8D-nK>&yq&OnM>n%tjSr2M2=_$euL=kOE6U%2@hc1=Jef!#v<E?Rp1_G)ZU3%I5zh4xw+RblNqvZpy;tNEy>s|)}f|FCW-MD<Lw3w-4=OO9;gu`YB9lv9KGbbBH?fbCl@cyl8a6Uw8bkPTL}Z^ctdW@=35(Muf6<>#WybfbnfL@5a}%W0hy|wI-`Ha#yr|2K%NE5)Z~nbnzX=-VOY~+1pa*3hGi1Me?KHjHOAFE_Q6+9=u#6ep^vzQn*j~wibZ}z&eSiQQ>5?@92-;erV}Le70wwqjqWEq-Mcq>zx`GB<Lmp+p6u^!_V#uSOWr^ig3yxbJc_YkXR=zEbf~#vX8ZA?(}3+npcz08!?q2Sx^O0PxQM^2Jl`j?Olsa_LBLi>;D_zF1{~ZV@%(T}EfCRi1VGad5rl3V_637QfGpkuTnkR=w5G^u=ydQd$P2iSTXGyy(n$bjAzcQ5J1zh?B)$OJ4qu|^iday`vn3H1o`UZ=0&RsRlZ#EDhsuuDzj(Djo|HH9Lty264~-nJbx={$>eCr+%l)r553cSV>^?vIWViR%Kc*i(J^bij-47mWbAm6EKomI-x>uk1p3+P{dO6T|RNJT(4M+R6C`<RzgOXo4g*TQFQ*R>hV*#ER`X)S|Qy0R~8i+plc5=~C#QZ4Q4JJjK4a(Tt+D-TFf~4uA-=y20Yw3JJJ29}DU+6m)buZ8slvjuY|7e7-To!_Q3C$M;Un`%8(J_$??^|eZ<fKs^+le6VdFHwS@TCxeA{z$~mXxA$CDR#JWB-?UDi%O-5ht+LVV>Xgsh6*Jgx{eXeQtEsrI8?Wm!*A1XrLXqZlD`59-{k988?tQuEL`7k%3M^@npy{q&6r4#Bb`Ea#|y8x;7IyordR-)oEg)D_7?;)fQ?vk$NxKE}#*@foEElH9tL7uh$ng6olZ_LQXOP*N(P+A0#zMT3}z?v*A6PN<@&gzaqs10n4k3s78hk1|w0(BvwpA#ulU}0}eF`fWUc47<oXlF5;;Y@|C-@kdK>^4vz6xGPRKk1Ys48CuK0sP8n~%ozIU8Bq|oCw>MREF35F+2|z5fAN3%hAs4G?l$jZ#ZBlwP8NDO2PNu3lX46%`S$xt!nBLeqy!W6Qd`gk9Uyj&33C($9$!BQ8%zLPp;%xy6T_?igV38#vO2o|TJOPj38-j(I)Af?~bfi=-#bw^{HV0FGakuxUXX&+v>DKSNcb@eAa!<=lg95TTZG04cWWgwju=*H{F}kwY$63KCnhNj$f&Pz}RP)t({eOT`kIHbWQKPbz2IWzjYapsaMW9qrj-<h>0TjT?bWt#KC~hsQWHxyz11~Bn7hWW_L#pcTTu-0=qm-)3&r1QLOi4158-=Wr!Kq+`@~z_^X8HW6S9o}RGyU}*dTHltm2i!6e$!r3f=K%oC5<aE7)YF1azYo+=q|)=oIB%De063Y(fUvp<CmR4)<E(ZmnG79@D=$3;s0dH-rWCoCw>1~y8HD29<@!ePS;Xksow7tPQoDFgi7Vlx=L2X)st%n&#yy|@!F3oyjFbCQm)5t$uw3Q@cf*ZGzS?q?G+A5IG1Z|(CkA!+r9I+d+Q3;?H_IK?`@YWyLE%LA;+U-b#m72WColeH5QZrHC1b7eUB|q6|she4A!qKk<PB?8%O}F0?KPxr$I#_TR|knVtd62+9r~&=}toS4KuGgpk@WhczJ$$0Y&p9RZo|GaTfkmo>R;)(|K0uAup83H4C9oN;K$zp@7CeELbYMO0lT|E|hIl30f*P(T*?m>&>i4Jo19FINX>TI5Mhe%vEuq-#?<B)y1N8ztLC|vVqqXYu3+8_PS8@Fm20k3byCR?ZqTUTooGf3KFw|Q&*Y>UV`bmA((Ii7<slFVH%BPaqQVRK=#l#$~g`;G9;_-AvrGL(Quzuz}!!NuIo*>@*9G!Z_3XP{=`c5Q6gV20$r#caiBhl*Ps#YxFSF*6B8h)ECu{{0xQ*JB#yj~ELP}hwQf0!-uGYxKirQBX(C`t@h}<QVPIJ&7!YD2(cEzy;>zi|IuWvo2)raq`IF1l&jQNC13i%DC5<JU8Z;V~5lPq%*@_eam4H1Hf3>3WlZl>E&aL^0^Uy|2FKkqhlX)7hYYEB_SRCv)lth(YL)HIBb`|(`5iZbk4?_z|3j}ooZlbnasPZo#LUfG`>%<Xzdo#UxzZADsJ%AD@nuRYGE$X%xl}s8N(aC|yq8G;F)Y)95XlVI7pqv?LPfFhxwM!rT{ou=o1~iJNp-(&}MU^#G{7S)DW>x(K(llB^MAMU#Q>T7t*WusP^!fUQsYxgDClQAUer3#C1DSkzwc%G!9KT`O^5db&L0`u+&re-AWepS$mC{>Y$7JUURatYWcQ}3(Gcv5mBPS^>bn9_{_h9!yZ|ke>_BT+arB^@f-F(u0@5;Zwy>;;TX?pEO_p|r9pFUIv28$cXZN4DJ!bw;wYTZYlK~bxi=Iqid+ucWh$T}dEWlWuBYRYUsxjgr?Sy|`FRqMD9jW4dGM27tAEuVRfBoP*kv1V0y>D6~#e7Br7Fw<f1M{=y$Jo$_5-T7zto7>eF>x66OvSO@4prtDMBn%}CFcB>yb1k#IjN~D4jkeR)m)(#5raW@+eCy!;EoGbD=bP#657PHH4<2U~{C9~BEP9bxQ2*~@LD6n17ARe`lfQV@d-iGfcUKSZ-9A1>{0CIWUd8',
    'extras_v2': 'c-oy=X>Z)d8U8Ln|6#reB%KwtvTVm#XHztaixf^{qf%S6!h)D3XH8Zlhvf`)#L$25^Ukrn)(5fyEOPkX^B&JkimH*VX8%>PUNET^Oy!*}O8k}St<d<}ZJSo6LgAavTfwuU{)oq-630ioR#q(ITF@&itStX-iGG*0Cv3RR%VO*4KH$}T>Dm$>;#T~x6H0pmtjb2z$4AFUKmGaYEn6FwIG2?OBX-7uxRfa`1A0_BZ-sekiqm`9-fl&m=E3pNukSD4fpc$q{P$nsSs0Pb%Xk0ykjx1D_v52X>{vp}Va>@Oyz{Qq(dzh!;iub2_e8%|=&r3zBw-iNR2Uko&loXBG091^c+ep%lcZ@Kbb5FCI*1}GMLeXU(JXv_^|ozgyI}w1WhcyYG*{$|+1q*F7Fsw%?}*X!kQH%tn-y)?AV{@V>+7}ym3SzWPUNk7tz;(FOZokB>Fm)}gTOc^jAZs5f{x{&r-+SS>zMI9>#9bD#sa9QRo9AytF$QAf8nJP5iL&qx5A`~(;P;Gkh)+?`D$ng!q=2M6{DDX-#-eS<nTqdkD>SazR)?Ny`4wSZfW2+VzN3|uup;FRZ|KTtk}(F!2({2R@=9yJ{>Gks5IA|^2!wAWLLuI4XfonB@~iBrhh``MI|bzBgz;Chk<=3%}-#;3U%9mqc{7-ML=p^;<M$kG-fT?K5Cc@0sM{^CEu1}LbhM`q*fv}tpeqzfJ}swFd9B%u@NmCX=%+FlQvyKACfeP7JW47=bT8ulp?dh)5@;S!t>>lJ!7FY`?R->%GN9{*m=Z?opX%W*}(on!5YneL+4-uDPx|diYY?Lt`**`m5HD=c(9Cg3sU4t%Lo3L_e6>Iu1Lk)Cs~(8P5y7CEJMdsGzrhL7JZPUMo*T<<_O|=vvFbFnaJLZBDop4M9v<f`Eku&FIP@v%p0^mlcgW?WJnn874;5}QemKA8l=w|GN(H;(r-qRH|z%%pU*5T<$YrEHJXIL#eKupYZmOVyCMr_+-@`6=UxO^X~nqh*vwdKp{di8@>JHfNOdpaQ2FQBr%|hT!}6Pb)x%5{<~E*wZGnA_(DZJ|l1+4Tdj8_Ya<wshu00T&ee4yvUOeqE`KV#395XKMv^vnTCY@?e>LtM{FG}${F_4Af%e}neXhr8&VlY@$Qx<w0Y*p0gVKsUz30bfb)<;aXtQ57C%YI}R$k3J-kkt>TFnIgWnCP>vK}Caz?Je>fg37_P8dS;-l1&pTYJv=Wuu*f1h!FF)NHKg5=>Kbtc~fM2tzIep&{ITd`g3c<*c~>jh-83Tj`68zC>;=(870;xbiHhvk3N_o9-^5KR=W$Ld7&u2Uiu|s!ovCT`3qWVVwL6sgVy+8Gvtug4e6)9RNNq<Zw+9O(q<+bwhrB_e`~l>D2;42?rihGUAcfUf?fsoh;e5!HHTlWuRnxWXehSv4Wnwe)0g5W7tfVthPf2A6~*RhR*?Jhn5DH9x=$EW0(Q-3yDxbJi9nhkznZt&kK9TkKC&)SzfohDX6&%wHcnAqz%H(N6tWJ(;5;_}!J3yBk%h3b)9VZ59Yu8pCO!oalIAqH;IKtfh=vBpc}yy`pNQeqIE+POck~Rya!K=$<}YuNbYSv!tX^Kw?pH$RlDcPbefc4H8sS9;7a3QyvigdJ282ybGz0cqwPQh$LK>*36zHUB=(<rO1fg7|zq&bZm@0lJu(BK^h=cq#?bYh+%m|FrQg+#{1bU5AS)C<GChzM%nW?mXzBIp}->dVN5d{O8)5uzh;pXR<GFI;o%rQ=Cgjx}d^2`RdhgDIBuU@{qc(w3crz9kb#=NfPO*dm(aNdr;8^zzP`-bWwB#?obIuIkDBcqD=6nMl#@~|6@f1hgZ9kx<RQK;xVl2qGfKtrZHW3MsjEB?^4#LMM5fwXh$CdqgjPOU9ZZ@cE}Bg@kD*jm(-f7u`bmF$2ST@p<Wb|28_fpwHQ&|O~s%q}gIF#aI9ikefoQbtlb7PSVJ15U{ylYD&s!els3H>ykN?AqtJS@ro#YXfX=h6r^8=cP4~&V758-f^;Zd>}=pC|TYKli6+RJ~|muEFK!PRBF=$QW_|!Hs>!o0x0ddh8n-lI-29q9TzI0<KBK+K=NqK*tfP$;MM$f6NlK{G4ar(y)y2ws)Matf{^wUiPIbgdYK8#^jZ~}V2>cQf}s`Nm5w^Sq0RvE*qK8p09HEHv`Qbp*&rHMgP^gL*W?hgT5|}Y2FRq&MLRYkrc+x;lRe4Aoik~?cu47GE~RqbYZ|;IPS0IU2*{k{(0zt!I^H0hbGb>%5W48nCH`0P{@p=b^Yg$Xhump)npQp@lkjChw)<R$<GbP`oxNQy4}l>z%0XdY&Tp72P^=TBg+9J$7q)1l&*4Q!w=f5$F9I~L#as_~7i@_*;MHq)4Prs&-uSmoM1?X4%am&vcgH$h+W4MrS_Qb#I|kg7PJ;ILA{x7W&VE=sW;}fV{2(6w$%K`8Y5Q_HCv*%RD`1cpE-tHY>p}ZnjJt+t{RXV}8)3QD2bkA`=LH-4yEgxR9<Ys@I`ofo5DPy2+OD3C3Kze@tsBa~fX;AR0*}#!kWI5MM3k2_ULHw)4Tj(##7lP{XX)+h10QA~27RAj3ua!&In&EF7<)awWjqaVMD(|waV_sdfAJZ2IyJ|Jow*1KPX2vTon+T1znuK-<m&Wf_n#r8wl}W;IL)KRQ9Rt6Y;U`;sgD&-!nbPJ^qs#q<7u}U-#@(>kl4{j1izV^*%2=O(sn~cbO2k@rLG&|y{*xF{2nlJ3}fG#KUC5)AbV&-4|(L_=pXlr^3EMkvHNBDxEdvFD@wtY=x>J&I-6Vu(mLe^jqBC$912^xrmGy?quw5s(xy(ZD5drE#&JwBjotK+GB1wL$8=7Ek~LxWb6{h}>>#m#PYFGO$e*eQ`)iN}5aiJDh;F%z%t@!+0E}L|nxXN}1aEe?I{gj%&mV{wiC3i%P55em2fhFQ1J~v$w1=g&-Dwmm7Xa?=DxGRz9rO*tT?7Tx3n*bA^Z!QV?kN',
}
def _load_release_module(name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name != name:
            raise
    module = types.ModuleType(name)
    module.__file__ = '<embedded ' + name + '>'
    sys.modules[name] = module
    try:
        source = zlib.decompress(base64.b85decode(_EMBEDDED_MODULES[name]))
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module
workbench_extra = _load_release_module('workbench_extra')
extras_v2 = _load_release_module('extras_v2')

ROOT = Path(__file__).resolve().parent
DATA = Path.home() / '.local' / 'share' / 'pi-workbench'
DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
TOKEN_FILE = DATA / 'access-token'
SETTINGS_FILE = DATA / 'tasks.json'
PHOTOS = Path.home() / 'Pictures' / 'CCD Camera'
NAME_RE = re.compile(r'CCD_[0-9]{8}_[0-9]{6}_[0-9a-f]{6}\.jpg\Z')
LOCK = threading.Lock()
WAKE = threading.Event()
NETWORK_LOCK = threading.Lock()
NETWORK_SAMPLES = {}
MEMORY_CLEAN_LOCK = threading.Lock()
LAST_MEMORY_CLEAN = 0.0
DEFAULT = {
    'website': {'enabled': False, 'url': '', 'interval_seconds': 300, 'last_check': None,
                'result': None, 'changed_at': None, 'message': '', 'history': []},
    'photo': {'enabled': False, 'interval_seconds': 3600, 'last_run': None,
              'result': None, 'message': '', 'history': []},
}


def get_token():
    try:
        fd = os.open(TOKEN_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        value = TOKEN_FILE.read_text(encoding='ascii').strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{40,100}', value):
            raise RuntimeError('Access token file is invalid; check ' + str(TOKEN_FILE))
        return value
    value = secrets.token_urlsafe(32)
    with os.fdopen(fd, 'w', encoding='ascii') as stream:
        stream.write(value + '\n')
    return value


TOKEN = get_token()


def load_tasks():
    state = copy.deepcopy(DEFAULT)
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
        for key in ('website', 'photo'):
            for field in state[key]:
                if field in raw.get(key, {}):
                    state[key][field] = raw[key][field]
            if not isinstance(state[key]['history'], list):
                state[key]['history'] = []
            state[key]['history'] = state[key]['history'][:10]
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return state


TASKS = load_tasks()


def save_tasks():
    # Caller holds LOCK. Atomic rename avoids corrupting config on interruption.
    temp = DATA / ('tasks.' + secrets.token_hex(6) + '.tmp')
    try:
        fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(TASKS, stream, ensure_ascii=False, indent=2)
        os.replace(temp, SETTINGS_FILE)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def valid_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        u = urlsplit(value)
        return (u.scheme in ('http', 'https') and bool(u.hostname) and
                not u.username and not u.password and u.port != 0 and
                not any(ord(c) < 32 for c in value))
    except ValueError:
        return False


def web_check(url):
    try:
        req = Request(url, headers={'User-Agent': 'PiWorkbench/1.0'}, method='GET')
        with urlopen(req, timeout=8) as response:
            return 'ok', 'HTTP ' + str(response.status)
    except HTTPError as exc:
        return 'error', 'HTTP ' + str(exc.code)
    except Exception as exc:
        return 'error', (str(getattr(exc, 'reason', exc)) or '连接失败')[:180]


def camera_shot():
    try:
        # A user may have started only the workbench since the last reboot.
        # Start the existing service only when an enabled photo task runs.
        check = subprocess.run(['systemctl', '--user', 'is-active', '--quiet', 'ccd-camera.service'],
                               capture_output=True, text=True, timeout=3)
        if check.returncode != 0:
            start = subprocess.run(['systemctl', '--user', 'start', 'ccd-camera.service'],
                                   capture_output=True, text=True, timeout=8)
            if start.returncode != 0:
                detail = (start.stderr or start.stdout).strip()
                return 'error', ('无法启动相机服务：' + (detail or '请检查服务配置'))[:180]
        deadline = time.monotonic() + 10
        last_error = '相机尚未就绪'
        while time.monotonic() < deadline:
            try:
                with urlopen('http://127.0.0.1:8091/api/status', timeout=2) as response:
                    state = json.loads(response.read(4096))
                if state.get('ready') is True:
                    break
                last_error = state.get('error') or last_error
            except (OSError, ValueError) as exc:
                last_error = str(getattr(exc, 'reason', exc))
            time.sleep(0.5)
        else:
            return 'error', ('相机启动后未就绪：' + str(last_error))[:180]
        req = Request('http://127.0.0.1:8091/api/capture', data=b'{"effect":"ccd"}',
                      headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(req, timeout=40) as response:
            result = json.loads(response.read(4096))
        if not result.get('url'):
            raise RuntimeError('相机未返回照片地址')
        return 'ok', '照片已保存'
    except HTTPError as exc:
        try:
            message = json.loads(exc.read(4096)).get('error', '')
        except Exception:
            message = ''
        return 'error', (message or '相机服务返回 HTTP ' + str(exc.code))[:180]
    except subprocess.TimeoutExpired:
        return 'error', '启动相机服务超时，请检查相机服务状态'
    except Exception as exc:
        return 'error', ('相机不可用：' + str(getattr(exc, 'reason', exc)))[:180]


def worker():
    while True:
        with LOCK:
            snapshot = copy.deepcopy(TASKS)
        now = time.time()
        site = snapshot['website']
        if site['enabled'] and valid_url(site['url']) and now - (site['last_check'] or 0) >= site['interval_seconds']:
            result, message = web_check(site['url'])
            checked = int(time.time())
            with LOCK:
                current = TASKS['website']
                if current['enabled'] and current['url'] == site['url']:
                    if current['result'] != result:
                        current['changed_at'] = checked
                        current['history'].insert(0, {'time': checked, 'result': result, 'message': message})
                        del current['history'][10:]
                    current.update(last_check=checked, result=result, message=message)
                    save_tasks()
        with LOCK:
            photo = copy.deepcopy(TASKS['photo'])
        now = time.time()
        if photo['enabled'] and now - (photo['last_run'] or 0) >= photo['interval_seconds']:
            result, message = camera_shot()
            finished = int(time.time())
            with LOCK:
                current = TASKS['photo']
                current.update(last_run=finished, result=result, message=message)
                current['history'].insert(0, {'time': finished, 'result': result, 'message': message})
                del current['history'][10:]
                save_tasks()
        WAKE.wait(5)
        WAKE.clear()


def network_details():
    """Read local interface addresses and observed traffic; never perform a speed test."""
    now = time.time()
    monotonic_now = time.monotonic()
    errors = []

    def ip_json(*args):
        try:
            result = subprocess.run(['ip', '-j', *args], capture_output=True,
                                    text=True, timeout=2, check=True)
            value = json.loads(result.stdout)
            if not isinstance(value, list):
                raise ValueError('invalid ip output')
            return value
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            errors.append(str(exc))
            return []

    addresses = ip_json('address', 'show')
    routes4 = ip_json('-4', 'route', 'show', 'default')
    routes6 = ip_json('-6', 'route', 'show', 'default')

    def gateways(routes):
        # Linux may report multiple defaults; prefer the lowest-metric route.
        selected = {}
        for route in sorted(routes, key=lambda item: item.get('metric', 0)):
            name = route.get('dev')
            if name and name not in selected:
                selected[name] = route.get('gateway')
        return selected

    gw4, gw6 = gateways(routes4), gateways(routes6)
    interfaces = []
    for info in addresses:
        name = info.get('ifname', '')
        if not name or name == 'lo' or '/' in name or name in ('.', '..'):
            continue
        base = Path('/sys/class/net') / name

        def number(path):
            try:
                value = int(path.read_text().strip())
                return value if value >= 0 else None
            except (OSError, ValueError):
                return None

        rx = number(base / 'statistics' / 'rx_bytes')
        tx = number(base / 'statistics' / 'tx_bytes')
        speed = number(base / 'speed')
        if speed == 0:
            speed = None
        rx_rate = tx_rate = None
        with NETWORK_LOCK:
            prior = NETWORK_SAMPLES.get(name)
            if prior:
                elapsed = monotonic_now - prior['time']
                # Reuse a recent rate when several clients request simultaneously.
                if elapsed < 0.8:
                    rx_rate, tx_rate = prior['rx_rate'], prior['tx_rate']
                else:
                    if rx is not None and prior['rx'] is not None and rx >= prior['rx']:
                        rx_rate = round((rx - prior['rx']) / elapsed, 1)
                    if tx is not None and prior['tx'] is not None and tx >= prior['tx']:
                        tx_rate = round((tx - prior['tx']) / elapsed, 1)
            if not prior or monotonic_now - prior['time'] >= 0.8:
                NETWORK_SAMPLES[name] = {'time': monotonic_now, 'rx': rx, 'tx': tx,
                                         'rx_rate': rx_rate, 'tx_rate': tx_rate}
        v4, v6 = [], []
        for address in info.get('addr_info', []):
            local = address.get('local')
            if not local:
                continue
            prefix = address.get('prefixlen')
            rendered = str(local) + ('/' + str(prefix) if prefix is not None else '')
            if address.get('family') == 'inet':
                v4.append(rendered)
            elif address.get('family') == 'inet6':
                v6.append(rendered)
        kind = 'wifi' if (base / 'wireless').exists() else (
            'ethernet' if number(base / 'type') == 1 else 'other')
        wifi_rx = wifi_tx = wifi_signal = None
        if kind == 'wifi':
            try:
                link = subprocess.run([shutil.which('iw') or '/usr/sbin/iw', 'dev', name, 'link'],
                                      capture_output=True, text=True, timeout=2, check=True).stdout

                def wifi_rate(direction):
                    match = re.search(r'^\s*' + direction + r' bitrate:\s*([\d.]+)\s*([KMG])Bit/s\b',
                                      link, re.MULTILINE | re.IGNORECASE)
                    if not match:
                        return None
                    multiplier = {'k': 0.001, 'm': 1.0, 'g': 1000.0}[match.group(2).lower()]
                    return round(float(match.group(1)) * multiplier, 3)

                wifi_rx, wifi_tx = wifi_rate('rx'), wifi_rate('tx')
                signal = re.search(r'^\s*signal:\s*(-?\d+(?:\.\d+)?)\s*dBm\b',
                                   link, re.MULTILINE | re.IGNORECASE)
                if signal:
                    wifi_signal = float(signal.group(1))
            except (OSError, subprocess.SubprocessError, ValueError):
                pass
        interfaces.append({'name': name, 'state': info.get('operstate', 'UNKNOWN'),
                           'type': kind, 'mac': info.get('address'), 'mtu': info.get('mtu'),
                           'ipv4': v4, 'ipv6': v6, 'gateway4': gw4.get(name),
                           'gateway6': gw6.get(name), 'link_mbps': speed,
                           'wifi_rx_mbps': wifi_rx, 'wifi_tx_mbps': wifi_tx,
                           'wifi_signal_dbm': wifi_signal,
                           'rx_bytes': rx, 'tx_bytes': tx,
                           'rx_bytes_per_sec': rx_rate, 'tx_bytes_per_sec': tx_rate,
                           'is_default': name in gw4 or name in gw6})
    interfaces.sort(key=lambda item: (not item['is_default'], item['name']))
    return {'interfaces': interfaces, 'sampled_at': int(now),
            'error': '无法读取部分网络信息' if errors else None}


def status():
    memory = {}
    try:
        with open('/proc/meminfo', encoding='ascii') as f:
            for line in f:
                if line.startswith(('MemTotal:', 'MemAvailable:')):
                    k, v = line.split(':', 1)
                    memory[k] = int(v.strip().split()[0]) * 1024
    except (OSError, ValueError):
        pass
    try:
        uptime = float(Path('/proc/uptime').read_text().split()[0])
    except (OSError, ValueError, IndexError):
        uptime = None
    try:
        temp = round(int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000, 1)
    except (OSError, ValueError):
        temp = None
    try:
        p = subprocess.run(['systemctl', '--user', 'is-active', 'ccd-camera.service'],
                           capture_output=True, text=True, timeout=2)
        camera = p.stdout.strip()
        if camera not in ('active', 'inactive', 'failed', 'activating', 'deactivating'):
            camera = 'unknown'
    except (OSError, subprocess.TimeoutExpired):
        camera = 'unknown'
    try:
        p = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=2)
        addresses = p.stdout.split() if p.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired):
        addresses = []
    try:
        disk = shutil.disk_usage(Path.home())
        disk_data = {'total_bytes': disk.total, 'free_bytes': disk.free}
    except OSError:
        disk_data = {'total_bytes': None, 'free_bytes': None}
    return {'hostname': socket.gethostname(), 'uptime_seconds': uptime, 'cpu_temp_c': temp,
            'memory': {'total_bytes': memory.get('MemTotal'), 'available_bytes': memory.get('MemAvailable')},
            'disk': disk_data, 'ip_addresses': addresses, 'camera_service': camera,
            'load_average': list(os.getloadavg()) if hasattr(os, 'getloadavg') else None,
            'reboot_required': Path('/var/run/reboot-required').exists()}


def diagnostics():
    processes = []
    try:
        p = subprocess.run(['ps', '-eo', 'pid=,pcpu=,pmem=,comm=', '--sort=-pcpu'],
                           capture_output=True, text=True, timeout=4, check=True)
        for line in p.stdout.splitlines()[:8]:
            fields = line.strip().split(None, 3)
            if len(fields) == 4:
                processes.append({'pid': int(fields[0]), 'cpu': float(fields[1]),
                                  'memory': float(fields[2]), 'name': fields[3]})
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    services = []
    for label, unit in [('工作台', 'pi-workbench.service'), ('CCD 相机', 'ccd-camera.service')]:
        try:
            p = subprocess.run(['systemctl', '--user', 'is-active', unit], capture_output=True, text=True, timeout=2)
            state = p.stdout.strip() or 'unknown'
        except (OSError, subprocess.SubprocessError):
            state = 'unknown'
        services.append({'name': label, 'state': state})
    return {'processes': processes, 'services': services}


LOGIN = r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>个人工作台 · 登录</title><style>body{margin:0;font:16px/1.6 system-ui,sans-serif;background:#151a17;color:#eef2ea;display:grid;place-items:center;min-height:100vh}main{background:#202822;border:1px solid #364139;padding:32px;border-radius:16px;width:min(380px,calc(100vw - 64px));box-shadow:0 12px 40px #263e2c15}h1{font-size:24px}p{color:#a3b1a4}input{box-sizing:border-box;width:100%;padding:12px;border:1px solid #4c5d50;background:#151e18;color:#eef2ea;border-radius:8px;font:inherit}button{margin-top:15px;background:#b5d2b6;color:#19281e;border:0;border-radius:8px;padding:12px 20px;font:inherit;cursor:pointer}#language{float:right;background:#2e3b31;color:#eef2ea;margin:0;font-size:14px;padding:8px 12px}</style><main><button id="language" type="button" aria-label="Switch language">English</button><h1 id="heading">树莓派个人工作台</h1><p id="description">请输入工作台访问码。</p><form method="get" action="/"><input id="access" name="token" aria-label="访问码" placeholder="访问码" required autocomplete="off"><button id="submit" type="submit">进入工作台</button></form></main><script>(()=>{let lang='zh';try{lang=localStorage.getItem('pi-workbench-language')||'zh'}catch{}const paint=()=>{const en=lang==='en';document.documentElement.lang=en?'en':'zh-CN';document.title=en?'Pi Workbench · Sign in':'个人工作台 · 登录';document.getElementById('heading').textContent=en?'Raspberry Pi Workbench':'树莓派个人工作台';document.getElementById('description').textContent=en?'Enter your workbench access code.':'请输入工作台访问码。';const input=document.getElementById('access');input.placeholder=en?'Access code':'访问码';input.setAttribute('aria-label',input.placeholder);document.getElementById('submit').textContent=en?'Open workbench':'进入工作台';document.getElementById('language').textContent=en?'中文':'English'};document.getElementById('language').addEventListener('click',()=>{lang=lang==='en'?'zh':'en';try{localStorage.setItem('pi-workbench-language',lang)}catch{}paint()});paint()})();</script></html>'''.encode('utf-8')


class Handler(BaseHTTPRequestHandler):
    server_version = 'PiWorkbench/1.0'

    def log_message(self, fmt, *args):
        # Never log the access token in the query string.
        pass

    def send_data(self, code, data, kind, headers=()):
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, code, value):
        self.send_data(code, json.dumps(value, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

    def authorized(self):
        try:
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            token = cookies.get('pi_workbench')
            return token is not None and hmac.compare_digest(token.value, TOKEN)
        except Exception:
            return False

    def do_GET(self):
        # The service is accessed on the Pi or via an SSH tunnel. Reject other
        # Host names as protection against DNS rebinding to loopback.
        if urlsplit('http://' + self.headers.get('Host', '')).hostname not in ('localhost', '127.0.0.1'):
            self.send_json(403, {'error': '请通过本机或 SSH 隧道访问'})
            return
        parsed = urlsplit(self.path)
        if parsed.path == '/':
            supplied = parse_qs(parsed.query).get('token', [''])[0]
            if re.fullmatch(r'[A-Za-z0-9_-]{40,100}', supplied) and hmac.compare_digest(supplied, TOKEN):
                self.send_data(303, b'', 'text/plain', [('Location', '/'),
                    ('Set-Cookie', 'pi_workbench=' + TOKEN + '; HttpOnly; SameSite=Strict; Path=/')])
                return
            if not self.authorized():
                self.send_data(200, LOGIN, 'text/html; charset=utf-8')
                return
            try:
                self.send_data(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            except OSError:
                self.send_json(500, {'error': '工作台页面无法读取'})
            return
        if not self.authorized():
            self.send_json(401, {'error': '请先登录工作台'})
            return
        if parsed.path == '/api/status':
            self.send_json(200, status())
        elif parsed.path == '/api/files':
            try:
                q = parse_qs(parsed.query)
                self.send_json(200, workbench_extra.listing(q.get('root', ['files'])[0], q.get('path', [''])[0]))
            except (ValueError, OSError) as exc:
                self.send_json(400, {'error': str(exc)})
        elif parsed.path == '/api/files/download':
            try:
                q = parse_qs(parsed.query)
                p = workbench_extra.resolve(q.get('root', ['files'])[0], q.get('path', [''])[0])
                if not p.is_file():
                    raise ValueError('文件不存在')
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(p.name))
                self.send_header('Content-Length', str(p.stat().st_size))
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                with p.open('rb') as f:
                    shutil.copyfileobj(f, self.wfile, 65536)
            except (ValueError, OSError) as exc:
                self.send_json(400, {'error': str(exc)})
        elif parsed.path in ('/api/storage', '/api/services', '/api/v2/history', '/api/v2/backup', '/api/v2/network', '/api/v2/shortcuts'):
            try:
                fn = {'/api/storage': workbench_extra.storage, '/api/services': workbench_extra.services,
                      '/api/v2/history': extras_v2.get_history, '/api/v2/backup': extras_v2.get_backup,
                      '/api/v2/network': extras_v2.network_check, '/api/v2/shortcuts': extras_v2.get_shortcuts}[parsed.path]
                self.send_json(200, fn())
            except (ValueError, OSError, subprocess.SubprocessError) as exc:
                self.send_json(400, {'error': str(exc)})
        elif parsed.path == '/api/network':
            self.send_json(200, network_details())
        elif parsed.path == '/api/diagnostics':
            self.send_json(200, diagnostics())
        elif parsed.path == '/api/fan':
            self.send_json(200, fan_control.read_fan())
        elif parsed.path == '/api/update':
            self.send_json(200, update_service.get_update_status())
        elif parsed.path == '/api/tasks':
            with LOCK:
                data = copy.deepcopy(TASKS)
            self.send_json(200, data)
        elif parsed.path == '/api/photos':
            names = sorted((p.name for p in PHOTOS.glob('CCD_*.jpg') if NAME_RE.fullmatch(p.name)), reverse=True)[:12]
            self.send_json(200, {'photos': [{'name': name, 'url': '/photo/' + quote(name)} for name in names]})
        elif parsed.path.startswith('/photo/'):
            name = unquote(parsed.path[len('/photo/'):])
            if not NAME_RE.fullmatch(name):
                self.send_json(404, {'error': '未找到照片'})
                return
            try:
                self.send_data(200, (PHOTOS / name).read_bytes(), 'image/jpeg')
            except OSError:
                self.send_json(404, {'error': '未找到照片'})
        else:
            self.send_json(404, {'error': '页面不存在'})

    def do_POST(self):
        global LAST_MEMORY_CLEAN
        if urlsplit('http://' + self.headers.get('Host', '')).hostname not in ('localhost', '127.0.0.1'):
            self.send_json(403, {'error': '请通过本机或 SSH 隧道访问'})
            return
        if not self.authorized():
            self.send_json(401, {'error': '请先登录工作台'})
            return
        path = urlsplit(self.path).path
        if path not in ('/api/tasks', '/api/fan', '/api/update', '/api/camera/service', '/api/camera/capture', '/api/memory/clear', '/api/files/action', '/api/services/action', '/api/power', '/api/v2/backup/config', '/api/v2/backup/run', '/api/v2/shortcuts', '/api/v2/speed'):
            self.send_json(404, {'error': '页面不存在'})
            return
        origin = self.headers.get('Origin', '')
        parsed = urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or parsed.netloc != self.headers.get('Host'):
            self.send_json(403, {'error': '请求来源不受信任'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= (7 * 1024 * 1024 if path == '/api/files/action' else 8192):
                raise ValueError('请求数据大小不正确')
            data = json.loads(self.rfile.read(length))
            if path in ('/api/files/action', '/api/services/action', '/api/power', '/api/v2/backup/config', '/api/v2/backup/run', '/api/v2/shortcuts', '/api/v2/speed'):
                if path == '/api/files/action': result = workbench_extra.action(data)
                elif path == '/api/services/action': result = workbench_extra.service_action(data)
                elif path == '/api/power': result = workbench_extra.power(data, update_service.get_update_status())
                elif path == '/api/v2/backup/config': result = extras_v2.configure_backup(data)
                elif path == '/api/v2/backup/run': result = extras_v2.run_backup()
                elif path == '/api/v2/shortcuts': result = extras_v2.save_shortcuts(data)
                else: result = extras_v2.speed_test()
                self.send_json(200, result)
                return
            if path == '/api/memory/clear':
                if not MEMORY_CLEAN_LOCK.acquire(blocking=False):
                    raise ValueError('清理正在进行中')
                try:
                    if time.monotonic() - LAST_MEMORY_CLEAN < 30:
                        raise ValueError('请等待 30 秒后再次清理')
                    before = status()['memory']['available_bytes']
                    result = subprocess.run(['sudo', '-n', '/usr/local/libexec/pi-workbench-memory'], capture_output=True, text=True, timeout=30)
                    if result.returncode:
                        raise RuntimeError('无法释放系统缓存，请检查清理助手权限')
                    LAST_MEMORY_CLEAN = time.monotonic()
                    after = status()['memory']['available_bytes']
                    self.send_json(200, {'ok': True, 'before': before, 'after': after})
                finally:
                    MEMORY_CLEAN_LOCK.release()
                return
            if path == '/api/camera/capture':
                result, message = camera_shot()
                self.send_json(200 if result == 'ok' else 500, {'ok': result == 'ok', 'error': '' if result == 'ok' else message})
                return
            if path == '/api/camera/service':
                action = data.get('action')
                if action not in ('start', 'restart', 'stop'):
                    raise ValueError('不支持的相机操作')
                if action != 'start':
                    try:
                        with urlopen('http://127.0.0.1:8091/api/status', timeout=2) as response:
                            if json.loads(response.read(4096)).get('recording'):
                                raise ValueError('相机正在录像，请先停止录像')
                    except (OSError, json.JSONDecodeError):
                        pass
                process = subprocess.run(['systemctl', '--user', action, 'ccd-camera.service'], capture_output=True, text=True, timeout=12)
                if process.returncode:
                    raise RuntimeError((process.stderr or process.stdout or '相机服务操作失败')[:250])
                self.send_json(200, {'ok': True, 'camera_service': action})
                return
            if path == '/api/fan':
                self.send_json(200, fan_control.set_fan(data))
                return
            if path == '/api/update':
                self.send_json(200, update_service.start_update(data['target'], data['action']))
                return
            web = data['website']
            photo = data['photo']
            if not isinstance(web['enabled'], bool) or not isinstance(photo['enabled'], bool):
                raise ValueError('任务开关格式不正确')
            url = web['url'].strip()
            if url and not valid_url(url):
                raise ValueError('请输入有效的 HTTP 或 HTTPS 网站地址')
            if web['enabled'] and not valid_url(url):
                raise ValueError('请填写要检查的网站地址')
            wi, pi = int(web['interval_seconds']), int(photo['interval_seconds'])
            if not 60 <= wi <= 604800:
                raise ValueError('网站检查间隔须在 60 秒至 7 天之间')
            if not 300 <= pi <= 604800:
                raise ValueError('拍照间隔须在 300 秒至 7 天之间')
            with LOCK:
                if TASKS['website']['url'] != url:
                    TASKS['website'].update(last_check=None, result=None, changed_at=None, message='', history=[])
                TASKS['website'].update(enabled=web['enabled'], url=url, interval_seconds=wi)
                TASKS['photo'].update(enabled=photo['enabled'], interval_seconds=pi)
                save_tasks()
                result = copy.deepcopy(TASKS)
            WAKE.set()
            self.send_json(200, result)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {'error': str(exc) or '任务设置格式不正确'})
        except RuntimeError as exc:
            self.send_json(500, {'error': str(exc) or '操作失败'})
        except subprocess.TimeoutExpired:
            self.send_json(500, {'error': '操作超时，请检查服务状态'})
        except OSError:
            self.send_json(500, {'error': '无法保存任务设置'})


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == '__main__':
    workbench_extra.ROOTS['files'].mkdir(exist_ok=True)
    extras_v2.start(status)
    server = Server(('127.0.0.1', 8092), Handler)
    fan_control.start_fan_controller()
    threading.Thread(target=worker, daemon=True).start()
    print('Pi Workbench listening on 127.0.0.1:8092 (use SSH tunneling for remote access)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

