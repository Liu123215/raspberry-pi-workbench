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
_EMBEDDED_MODULES = {'workbench_extra': 'c-qBTTW{RP6@K4eF;yQ(wkv97*{&@>1yU(_D3ZvqleU1e5GZn1%Pg0}l0#i02#Dc2HVi9q5j&|XwUHaU4cc06o77I?sQxqJuJqKukaK2+T#~z5tz83E5bRvfea`s~JvKHr%lwFkmg`f8c+9pu(r`UmB@t(#wTuHAuDCWOmhX^&t<sRNfQA-#;i5S<Hdb-l0Sh@<vLbr+bUI^EI*OVxcfD*DF9jj9X%tl&A#0Ps;!V$8B5L~rOyx!#da!PW^w%+sc)Aa(z}+t#p<&3v^uXH}Uw;+nDZh6k=2t2g=jY$LL}ti_hRQ|Sv|wa5S)1wxnIPIPS=d^lzTG6Ri33%l1x?1;fTI^&o5vxX!O86G9GSJ+U=O_FuvOn<mNVeiT(-4YdE=E|Exvu>_4!xkK%_I|M`W^g>a_Z)R2<qMK%RLkR1X>BRbitUO*5t|1pZvuhGpWz|E^D@YG42{k6iGk<=a%pOX$VWz)g?(V#OdoC8ulW&q`AG2d<AO`Gw`hR2WXzI-l-#?p*Kw{x_XZt{psme6YXO-QUv;aRZ$ULJOt~C`R2(Wi?XiP;<%5bfZOU3ASU7W&k-f)6`Jv+?l`%dGw<4{E*Bsp?QOO9$O`z>$jpRaIn4Das6evKzP&Q5WKFBVQRNvpEFp5pvGGe`8=d_T2TzCZ?*9*$O|tcYKpN>Njru>^yvyb0n3IE_le7awiPZ@bVbCe<(Ptq4UffjERME9lZnL!&_iX1>z}{c8&8Ov*&(oUwueTJ*4wD4ZuIC3w&lUsTZdQn5BHuOeY)5E`=67Ko*aGrpU#I5lsUndvB&eA``xR~{6K0Z(t;SMc$C|y74?VvH7`r&;r)VNLke#!B_`j5=SCbnG4M?|Zb)rNSnD8q|J%t#M-j85Xg8STZPqVicY80{zXOsc4}X{Je4(UsIc-P4YN6h9Eb5-4&1qO74*Y{5zOtDQ>cuo$<l%bpM1+nBOnBd1c_Sl@@|actnbFZVGzeb`87MGu0BK1oDppdRVKs8!!&4Clii<dbwKj9yhD)7nz0KV=-RyCrYc>rynZG3LGeiUBzzq%EfcX&Jr;EIS%yAVKrH?dp5{f5MmL{}82_Sz{M;Fs7Y0>o=&uT9@7FnAnI=XUgAyutj#fi|nZrTuykPaN(FpP!i$y%*e-;^N)uNJD74smTM>-U1B3S|xKi+d)#XI+X2vi4Slm>^(rRT5Q^p_0MSC}bj5bWP+Iq$d&%)p7xW^MWwqfMA`Er&7w7?oLxaZVEa$#$UnIL@JPkWj3A=$v8cwz4J~sKPi#OT%6q6lG!;Y*D)plvGiWngM@}$jJ#21W{9#$;nAe@j;T7Ss`8jg*C5WKQ4?WuefQ|@{c`dtWWpX`F~iu`7qn%Up$${-p<a@=0a0jM0fK`?7V{wHGjD}4cm&@NEX+*R3f@zhQoa<MIVam3O#S7Z?q8lJS05zXf9%|T-2K~KB{TJMk=1VDqv%BzjN$;%$M6`VtBbuj%Q;0+0UjXG|1l=ze63b{2~p}$kxo_A$ZDm6@;J>^Aj(7eKq*Bzk_NAO0FhVdB4_%*xHXJ|*~FzZcu`TY@I0j*N>yj~TJq#yg;G^~UNSI>lmsKOk*g|cIOU8`ymj)!ES?|s3XiUBCBNNAFYSIK3$9kIZ^}zj5MkfEq){mh`U+=SoY2KHs!uVO&YpHCzB;`Z(dtl|<5w(CU?A~~ixR0i_^SAU^go)iHx9nrO+L7q?0wT0kIJTq)0Gqm)q9=7C=8M<Kq`M#C|QE5$5#)ZU4tIujh~fxt-8D^U61{guB|P>^Rpt-=x5Y0S3@YmnOv2Avk&xa=k}w{&C7_}Ki)dn-zg%y4UM&+#-n9baaIjy8aM+m7C?Zi#F}Z}V~SJxSVJI#_?5-N*|lr~2_Pz<VHI&2APUh6A}JP`tCrW&k#tpc5~6RIdCdYfOOcG17pChdnj@$>3i?H9`jd4|GQ&#e7=?#iFOX~GQlXHj-vI*y8vhWmlz0_#Qz^JmwqX#o05;K%Kknhp6eJ#dL0TMcO!gfa1{yO}tSG7+gJ%_36z<oS*12fl6=F^MdBI)*RR_zq`08LfZq!<gBaEwDLtcu+6mTk}so^D<ZfKlw%Y%_)iV>F4NPuI<!~wF0zER9^u$e}({9=;DB|MtYrKMo*l|S2d#%=Kp!BjWJ=LdIuHT@`&t>*)s%O0^0pG51>h_-F+A(ioQ5L7?`HyTHzx`M=!_pxAwu9b1i8T7sbBlrp3AXg?lwj2$T;avunwY)wd#$&}D$3Cu1)#M4EjR)W*0p&-Rt5*f2iTipW#Y-4VG&N{6gb}gd^4Y2o0hNF~9e<Ug;**J*(l9g@#?L_;F<sv*MNaBzxUM89hQMNf#~~#u^%@fYAKO*n+r@B!o_kQVptL|xHQ+jG8*&N%vLR&GKr=?p*gIRvjeCW>E%5+KAZg~lSTw2KT9h)W*a$`sOcp$MJWig;L<$DN=RW21KzUO5KCfMJ|DT6nJ<y<0oPs{_gc4QMRPrk%XHiwvH%eV=avn@iOiZ5oiCKgHCa2HU&QDHQfjfb57~@yQtThnDH!L^&@`>X&OjCS3)I-qMa`bbP=T8}Z;GqP)#dR!pHkZgc1iTaCS1~P(6>($~XrWq<dwYj__q*F)cXqx7l$KoisC(ma=l#q7{qE-BqbJGL>z&Wv?|k+^9w-5hj5&q|vR%l@Q!lI1JMBi~P5k%<3KSMaX&xZD@ZC^y=ujk=GgY>)%r%Nhq?VnBp99#I#>mW&T;AzC{8QNgFVU!~qUx%oR%M9%{L=iJa{|+fRS{BfGWRa11?Rv4uxhFaSSM!)*r;aT&<)x5z*@eQD3}dNRLLy!eJT>xMcTm1D6fwI%hP{cc(FP*C>hqP$3m2T%rauanKCK^;FRK+%Rtx*O^Gj}>0YsJ%Jl5|Jp~#T;Fm&MenK$!c|K>iOWAOc{rgbX%L+)58pXd1i8@y$ae!S@r1+OgUAeI33s*>&5b7cNL2|6o7`<e5Z~wdV?X7ajvix;@MKYEcz>qC%?E4}QA`)9c=1OLB1<3<)8_Kt{{Z;3af5@kQ_-y;|-c4zn?iX9htq+qAwhkYqE$oXFM;1I!F|7S>#V~I-Sq!Bv%E@0o?LPgi^M@-(cW<3sB)<p36JIX', 'extras_v2': 'c-qBTTW{OQ6@EA1|1f<pNG38Z$4NF&mRoeaDYnSA32L`RYX}5Ijv}skD`)7-2LA8;&RobLDcb>BpfX^QGv}N+_sb|Ro4S?kS5a3BR*MA_yH4f>zU%awOMG{mrma&huqSsdPqMuFg2%k%hX>oXE?JgHPOmK2wCuYE`mL@kV3WvQk#8*AXS|x7t}U<;w*2267t#V?wQhKIcyM^|;~y?Qut=eVySn6lz)qMK7Im5w9zBX((sK3G<j1#ld%fXRy7LYXe))9%5tu#e;a`7&WPU(2&p-a{b36mE`-cY^-?EsN{VE}O@Sb#q3|5B+3?JFvn<x6TTy|}xGzq?vO!&Uy`h*d35E7kO@;m8+vzktdyiRV9-+4ixsqnj$H<J0EE<Utv-7eVQlcMA5IhY@0nCbbvZF9*Dqc?<Tafpksyw390Z=j?~is-WK0LAZeA>;bmyq0ywqh<Zwa%uRHWdp?+Arxiy5=zIiH$a5yTrHTAJ?qLw_=*D@QHieQaU#+@kN%hxf(NuXkzW(5MVRiugb%6<wyfW}j6i)&k)(X2Q!D!yF5?|!soQ(sN`0Hl9V6S$HK$GL8H|v)_7?1`Cz7%$xbRl&YQ11yQt(#lw}-(UG>|W3B0FIZ6VQ`h@q_oQs&C1m;QS%|^NkcGFL4|}hG5wD^gEsW0HiDz*TWvY=^dkiS|$ayHI9Z+Yw_k@f@Kg$Zj!u6HU*!6_3IW?Q-sk<Kz{XzMF<I|Au|>m-a?R;)(kUg)5WwAr(Uoav`HT$L=2=9o&}t??yAf`T`t)R=4-Z(2i_=b)#8Gk1}xti!ICO-_|FBnk?b$X9E`(d)YJ4}(ono@xfN@rG^iPNmf>z*3SVgxM;`Sa3*O%3DWA(!S4Cct{F}Nie1nuXagt>%@*q(S9yE^j5$N%1ZPdC|n!Ornay=4>gxv@8L&V-KSB7MmG)R5QOTX-57cl4#8U!A>f^)!BNsloyhdWW!uSS&D?0XiT&NwXU+gSN)Fj0Zg`<g`&^R}=q&%7D7F^1V5ND!Brj4{W0hFWn+nVt?$>#E|Z94PDy{~hc!N)_+f?y8S^u*v+L)~8)tz^(z3-W74O4z7+*U%y_i)(X$02SU@2!$Bq&PczJJl(57OH7@O>*psp*nW_i1l)#lGC6XKN&_eM|EIqfhBJ&IG6jsp`xg0B7<P~yQg&a#n7OVjG0jpb9@JiEVKd>`+Xq)7qH54b``*7DN?X#{yL<5NR99e@Pa!{?DNZEq2N<w)>EkoiMYR(Y>qW<P7itnED|5Tyg<XL~JJ(NDkDZEhmxm9Geh1DuF=^>UwY~>BP0~9lZ#M%UIpiTABD$~b9Fq1)_Zj`8ANQ>{5c8QR%aJqc;nwFYSq&tp6tK_d3d`QZM&Zln*ZUE6<gEmM=Rg)E3hio>yHHi=ijchf}Y;(n37=<xvy>i%yC5B~64nJRBe)cbrP;}yRwW`f&L-DK8=Sm}kUDDc$bn`F^$UZz~Zmo&-4x>UquUT)mArB={lV;1WOj>D6ZdpS=b(N>qP~$dD@u8dBFhzKwcQMH$uPfj8PDAwvZr+>)x`nMf8J)rJNUO7E;;RQD>5d8)1lFAtv?0;t+{dNpE22MT4rNjC9lSuXTv9!x`kS<HIv`m-R&UP8`X!gUnzE;NdH&gZ81;*$U1W)%mDMvGswQm8qAIZ8dO8+39Y_Tgk%BX+8k%g>a86yWkk1<DJrntF)T}HW2Qe+bc6+fpIZ*_|w5YpmTcCRl)4Du~<E*}|ey^%h^lGU--e9ZKHvuUFp3~Ho;I8p^s51K8@0mfI#0aG#FlCWd+wPZn<-dLN=IrglVjUBaAQ<DCm{-}1ZGd?_-d6{|jE02TCt$VnyJ!zjdt#PU!br#Hq%%BjIC3e+1j8A$gTf^tqpD!+7J49E(Lgd3N5SFpnb>0#>y)Dq{OZ{ji`azu4Sw(2<{io*AGYVk<)(39NWvHF9Xg9Lxf@Wz<?@ue!c#3d(Rgsn<R(e4yXN^Cso{oZo>%1Xnd9-I?$D$fuboVipHW%RTnRNno}d53&UNpi<bkI1Dxv&9Awd40R}#%58lxR(l8mojtB}GtCAyS`<sqolstp)gbA}03wI~G{DK(2UX!b{1!RIy60z;g>Ea){`sO+j++6T&GOlQNQKk0?%ySm2GriMKdbFS{=T~es>MaEm}c%<<07?1c8b#cR0K4??3X=DpRe%F8|6*mWz*h{6FT4`_+(qg%4dmeS9SDYQ@BBmjEP>GPEHN{_~g}|%&Hg%fN&2YW1Ke^EADLe4GAvNjQ8#Ay`5NL=z<Ln-QnlMg9O`-wO$r73YlGw0Ay%V@JN7E{8eltU4FV|XWQjtIiO__iQl??_14+hjsgf#2=)DOiOzcDP07gvwFjFMhbyHc<cxq<pdHT_bqa$;?4pc;L@iYy;z(N$IWkNDHaz1`qXjznhOp^ifpz;SZ{Sr){*4M+&S&A-r%g$YQvoi-T-&PJ=cIkZ`3p|eczSgabjg&HZJY+>yw>H_7dX$F2{<{6tJhdmRHx|JQcH5qV0xL5XV9Z(QCDw|@tHZiE~(%P+pDj$LZ5~M?6k}i?sUkCG6`ILPh83K6t?$zE&<3}YcvlRP~I;FV-IGTVrrfzh)`nH5SLN%I1X&&iJMVg~CyFXIQq_Y4(*fn&z?^cRP*NLG_sD)r;Xp3hAiF$X^{6u@ih(?)yY=KDq59R~wxQOE5VAf4y(MC(#RnzipOzB*$B5KuS;cp5w-E`}xBjpL>CIyxBd!k<f!5TB&exVDihkaeW-gATDeIMM|nAsihgE1FOy^fuFpsmKLXne7J?6H^qMR!=$x4ymW4m+8uNpY+0{=B1q9+gMg<<ZYae?Gc6KHC1v^-W}GnX8LE;?uokH9Ib_zL`e@+}z8Sqn43;1`eKZUlw_FE!^7X9Dxc*w0(V!xjpT*XS&90-?imq`9~pkEtQx@^N?`~-@uKs5L&Cz@+kEOR8+pfN)vt@p7w@XFX&V8_H<Af^1+@li+<lQ?WLpUd1KgfF`nZ-s4vPUvq|p%r~es>T^fTwZig$k0bZNpLNnukp>RqZ<`M}k6vh2&lyO>K@I>(8Hykz6Os?$p-5D989d){TM5G{^$V3Tedi_6!nA&lAW1y%|c!`4Z#(!&n-XK=A%rPaH2}4SKiKHuFIZVsXvbx70vm7~xfwQP6vwh84wTMnmz<@~OTki%V*H&Hfaxr2#pnGjabJ7K@F%6!*oz35mh`l#0jqbLbV)VZ;%kYcfrF!!9^+;sA2DK&O7@f_pXB6v^HxvkS_v=wDAn$vI=*a%hkk+s+<^KSuSu~s'}
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
    server_version = 'PiWorkbench/2.0'

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
                with p.open('rb') as f:
                    size = os.fstat(f.fileno()).st_size
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(p.name))
                    self.send_header('Content-Length', str(size))
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.end_headers()
                    try:
                        shutil.copyfileobj(f, self.wfile, 65536)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
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
            if path != '/api/v2/shortcuts' and not isinstance(data, dict):
                raise ValueError('请求格式不正确')
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
                    workbench_extra.check_camera()
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
