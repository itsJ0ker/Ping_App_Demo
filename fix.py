import codecs
path = r'c:\Users\Joker\Downloads\testtt\ping-app.html'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

start_idx = content.find('<script>')
end_idx = content.find('</script>') + len('</script>')
if start_idx == -1 or end_idx == -1:
    print('Error finding tags')
    exit(1)

new_script = r"""<script>
let peer, myPeerId, partnerPeerId;
let currentCall = null;
let incomingCall = null;
let myName = '';
let partnerName = '';
let roomCode = '';
let dataConn = null;
let callTimerInterval = null;
let callSeconds = 0;
let isMuted = false;
let localStream = null;
let isPartnerOnline = false;

let ringCtx = null;
let ringInterval = null;

function generateRoom() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
  let code = '';
  for (let i = 0; i < 4; i++) code += chars[Math.floor(Math.random() * chars.length)];
  document.getElementById('roomInput').value = code;
}

function joinRoom() {
  myName = document.getElementById('myName').value.trim();
  roomCode = document.getElementById('roomInput').value.trim().toUpperCase();
  if (!myName) { showToast('Enter your nickname first'); return; }
  if (!roomCode || roomCode.length < 2) { showToast('Enter a room code'); return; }

  if (!ringCtx) {
    try {
      ringCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch(e) {}
  }
  if (ringCtx && ringCtx.state === 'suspended') {
    ringCtx.resume();
  }

  document.getElementById('joinBtn').disabled = true;
  document.getElementById('joinBtn').textContent = 'Connecting…';

  initPeer();
}

function initPeer() {
  const peerId = 'ping-room-' + roomCode + '-A';

  peer = new Peer(peerId, {
    config: { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] }
  });

  peer.on('open', (id) => {
    myPeerId = id;
    showCallScreen();
    setStatus('online', 'You\'re in the room — share the code with your partner');

    peer.on('connection', (conn) => {
      dataConn = conn;
      partnerPeerId = conn.peer;
      const onOpen = () => {
        conn.send({ type: 'hello', name: myName });
        setPartnerOnline(true);
      };
      if (conn.open) onOpen();
      else conn.on('open', onOpen);

      conn.on('data', handleData);
      conn.on('close', () => setPartnerOnline(false));
    });

    peer.on('call', (call) => {
      incomingCall = call;
      showIncomingRing(partnerName || 'Your partner');
    });
  });

  peer.on('error', (err) => {
    if (err.type === 'unavailable-id') {
      tryAsSecondPeer();
    } else {
      showToast('Connection error. Try again.');
      resetSetup();
    }
  });
}

function tryAsSecondPeer() {
  if (peer) peer.destroy();
  const peerId = 'ping-room-' + roomCode + '-B';
  const partnerId = 'ping-room-' + roomCode + '-A';

  peer = new Peer(peerId, {
    config: { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] }
  });

  peer.on('open', (id) => {
    myPeerId = id;
    showCallScreen();

    partnerPeerId = partnerId;
    connectData(partnerId);

    peer.on('connection', (conn) => {
      dataConn = conn;
      partnerPeerId = conn.peer;
      const onOpen = () => {
        conn.send({ type: 'hello', name: myName });
        setPartnerOnline(true);
      };
      if (conn.open) onOpen();
      else conn.on('open', onOpen);

      conn.on('data', handleData);
      conn.on('close', () => setPartnerOnline(false));
    });

    peer.on('call', (call) => {
      incomingCall = call;
      showIncomingRing(partnerName || 'Your partner');
    });

    setStatus('online', 'You\'re in the room — ready to call');
  });

  peer.on('error', (err) => {
    if (err.type === 'unavailable-id') {
      showToast('Room is full (max 2 people).');
    } else {
      showToast('Connection error. Try a different room code.');
    }
    resetSetup();
  });
}

function connectData(targetId) {
  const conn = peer.connect(targetId, { reliable: true });
  dataConn = conn;
  
  const onOpen = () => {
    conn.send({ type: 'hello', name: myName });
    setPartnerOnline(true);
  };
  
  if (conn.open) onOpen();
  else conn.on('open', onOpen);
  
  conn.on('data', handleData);
  conn.on('close', () => setPartnerOnline(false));
  partnerPeerId = targetId;
}

function handleData(data) {
  if (data.type === 'hello') {
    partnerName = data.name;
    setPartnerOnline(true);
    if (!partnerPeerId) {
      partnerPeerId = dataConn.peer;
    }
  } else if (data.type === 'ring') {
    partnerName = data.name || partnerName;
    showIncomingRing(partnerName);
  } else if (data.type === 'reject') {
    stopRingTone();
    showToast(partnerName + ' is busy right now');
    resetCallUI();
    document.getElementById('partnerAvatar').classList.remove('ringing');
    document.getElementById('partnerStatus').textContent = 'Online and waiting';
    setStatus('online', partnerName + ' is here ♥');
  } else if (data.type === 'end-call') {
    if (currentCall || incomingCall || document.getElementById('ringOverlay').classList.contains('active')) {
      showToast('Call ended / cancelled');
      hangup(true);
    } else {
      hideRingOverlay();
      resetCallUI();
      document.getElementById('partnerAvatar').classList.remove('ringing');
      document.getElementById('partnerStatus').textContent = 'Online and waiting';
      setStatus('online', partnerName + ' is here ♥');
    }
  }
}

function setPartnerOnline(online) {
  isPartnerOnline = online;
  if (online) {
    if (!currentCall && !incomingCall && !document.getElementById('ringOverlay').classList.contains('active')) {
      setStatus('online', partnerName + ' is here ♥');
      document.getElementById('partnerStatus').textContent = 'Online and waiting';
    }
    document.getElementById('partnerAvatar').textContent = partnerName ? partnerName[0].toUpperCase() : '♥';
    document.getElementById('partnerName').textContent = partnerName || 'Your partner';
  } else {
    partnerName = '';
    setStatus('', 'Waiting for your partner to join…');
    document.getElementById('partnerAvatar').textContent = '?';
    document.getElementById('partnerName').textContent = 'Waiting…';
    document.getElementById('partnerStatus').textContent = 'Your partner hasn\'t joined yet';
  }
}

function showCallScreen() {
  document.getElementById('setupScreen').classList.add('hidden');
  document.getElementById('callScreen').classList.add('active');
  document.getElementById('roomDisplay').textContent = roomCode;
  document.getElementById('partnerAvatar').textContent = '?';
}

function initiateCall() {
  if (!isPartnerOnline) { showToast('Your partner isn\'t online yet'); return; }
  if (!partnerPeerId) { showToast('Reconnecting…'); return; }

  if (dataConn && dataConn.open) {
    dataConn.send({ type: 'ring', name: myName });
  }

  playRingTone(false);
  setStatus('calling', 'Ringing ' + partnerName + '…');
  document.getElementById('partnerAvatar').classList.add('ringing');
  document.getElementById('partnerStatus').textContent = 'Ringing…';
  document.getElementById('callBtn').style.display = 'none';
  document.getElementById('hangupBtn').style.display = 'flex';

  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      localStream = stream;
      currentCall = peer.call(partnerPeerId, stream);
      currentCall.on('stream', (remoteStream) => {
        document.getElementById('remoteAudio').srcObject = remoteStream;
        stopRingTone();
        onCallConnected();
      });
      currentCall.on('close', () => hangup(true));
      currentCall.on('error', () => {
        showToast('Call failed');
        hangup(true);
      });
    })
    .catch(() => {
      showToast('Mic access denied — please allow microphone');
      hangup();
    });
}

function showIncomingRing(name) {
  if (document.getElementById('ringOverlay').classList.contains('active')) return;
  document.getElementById('ringAvatar').textContent = name ? name[0].toUpperCase() : '♥';
  document.getElementById('ringName').textContent = name;
  document.getElementById('notifTitle').textContent = name + ' is calling';
  document.getElementById('ringOverlay').classList.add('active');
  document.getElementById('notifBanner').classList.add('show');
  playRingTone(true);

  if (window.Notification && Notification.permission === 'granted') {
    new Notification('📞 ' + name + ' is pinging you!', {
      body: 'Tap to answer on Ping',
      icon: ''
    });
  }

  setTimeout(() => {
    document.getElementById('notifBanner').classList.remove('show');
  }, 6000);
}

function answerCall() {
  if (!incomingCall) return;
  stopRingTone();
  document.getElementById('ringOverlay').classList.remove('active');
  document.getElementById('notifBanner').classList.remove('show');

  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      localStream = stream;
      incomingCall.answer(stream);
      incomingCall.on('stream', (remoteStream) => {
        document.getElementById('remoteAudio').srcObject = remoteStream;
        onCallConnected();
      });
      incomingCall.on('close', () => hangup(true));
      currentCall = incomingCall;
    })
    .catch(() => {
       showToast('Mic access needed to answer');
       rejectCall();
    });
}

function answerFromBanner() {
  answerCall();
}

function rejectCall() {
  hideRingOverlay();
  if (dataConn && dataConn.open) {
    dataConn.send({ type: 'reject' });
  }
  if (incomingCall) {
    try { incomingCall.close(); } catch(e) {}
  }
  incomingCall = null;
}

function hideRingOverlay() {
  document.getElementById('ringOverlay').classList.remove('active');
  document.getElementById('notifBanner').classList.remove('show');
  stopRingTone();
}

function onCallConnected() {
  setStatus('in-call', 'In call');
  document.getElementById('partnerAvatar').classList.remove('ringing');
  document.getElementById('partnerAvatar').classList.add('in-call');
  document.getElementById('partnerStatus').textContent = 'Connected ♥';
  document.getElementById('muteBtn').style.display = 'flex';
  document.getElementById('hangupBtn').style.display = 'flex';
  document.getElementById('callBtn').style.display = 'none';
  document.getElementById('audioViz').classList.add('active');
  document.getElementById('callTimer').style.display = '';
  startCallTimer();
}

function hangup(isRemote = false) {
  hideRingOverlay();
  if (currentCall) { try { currentCall.close(); } catch(e){} }
  if (localStream) { localStream.getTracks().forEach(t => t.stop()); localStream = null; }
  if (!isRemote && dataConn && dataConn.open) dataConn.send({ type: 'end-call' });
  
  stopCallTimer();
  resetCallUI();
  if (isPartnerOnline) {
    setStatus('online', partnerName + ' is here ♥');
    document.getElementById('partnerStatus').textContent = 'Online and waiting';
  } else {
    setStatus('', 'Waiting for your partner to join…');
    document.getElementById('partnerStatus').textContent = 'Your partner hasn\'t joined yet';
  }
  document.getElementById('audioViz').classList.remove('active');
  document.getElementById('partnerAvatar').classList.remove('ringing', 'in-call');
  currentCall = null;
  incomingCall = null;
}

function resetCallUI() {
  document.getElementById('callBtn').style.display = 'flex';
  document.getElementById('hangupBtn').style.display = 'none';
  document.getElementById('muteBtn').style.display = 'none';
  document.getElementById('callTimer').style.display = 'none';
  isMuted = false;
  document.getElementById('muteBtn').classList.remove('active');
  document.getElementById('muteBtn').title = 'Mute';
}

function toggleMute() {
  if (!localStream) return;
  isMuted = !isMuted;
  localStream.getAudioTracks().forEach(t => t.enabled = !isMuted);
  const btn = document.getElementById('muteBtn');
  btn.classList.toggle('active', isMuted);
  btn.title = isMuted ? 'Unmute' : 'Mute';
}

function startCallTimer() {
  callSeconds = 0;
  clearInterval(callTimerInterval);
  document.getElementById('callTimer').textContent = '00:00';
  callTimerInterval = setInterval(() => {
    callSeconds++;
    const m = Math.floor(callSeconds / 60).toString().padStart(2,'0');
    const s = (callSeconds % 60).toString().padStart(2,'0');
    document.getElementById('callTimer').textContent = m + ':' + s;
  }, 1000);
}

function stopCallTimer() {
  clearInterval(callTimerInterval);
  document.getElementById('callTimer').textContent = '';
}

function setStatus(type, text) {
  const dot = document.getElementById('statusDot');
  dot.className = 'status-dot';
  if (type) dot.classList.add(type);
  document.getElementById('statusText').textContent = text;
}

function playRingTone(isIncoming) {
  stopRingTone();
  if (!ringCtx) {
    try {
      ringCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch(e) {}
  }
  if (ringCtx && ringCtx.state === 'suspended') {
    ringCtx.resume();
  }

  const playBeep = (freq, start, dur) => {
    if (!ringCtx || ringCtx.state === 'closed') return;
    try {
      const osc = ringCtx.createOscillator();
      const gain = ringCtx.createGain();
      osc.connect(gain); gain.connect(ringCtx.destination);
      osc.frequency.value = freq;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0, ringCtx.currentTime + start);
      gain.gain.linearRampToValueAtTime(0.3, ringCtx.currentTime + start + 0.01);
      gain.gain.linearRampToValueAtTime(0, ringCtx.currentTime + start + dur);
      osc.start(ringCtx.currentTime + start);
      osc.stop(ringCtx.currentTime + start + dur + 0.01);
    } catch(e) {}
  };

  const ringOnce = () => {
    if (!ringCtx) return;
    if (isIncoming) {
      playBeep(880, 0, 0.15);
      playBeep(1100, 0.2, 0.15);
      playBeep(880, 0.4, 0.15);
      playBeep(1100, 0.6, 0.15);
    } else {
      playBeep(440, 0, 0.4);
      playBeep(440, 0.6, 0.4);
    }
  };

  ringOnce();
  ringInterval = setInterval(ringOnce, 2000);
}

function stopRingTone() {
  clearInterval(ringInterval);
}

function copyRoom() {
  const url = window.location.href.split('?')[0] + '?room=' + roomCode;
  navigator.clipboard.writeText(url).then(() => showToast('Link copied! Send it to your partner'));
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2800);
}

function resetSetup() {
  document.getElementById('joinBtn').disabled = false;
  document.getElementById('joinBtn').textContent = 'Enter Room';
}

window.addEventListener('load', () => {
  const params = new URLSearchParams(window.location.search);
  if (params.get('room')) {
    document.getElementById('roomInput').value = params.get('room').toUpperCase();
  }

  document.body.addEventListener('click', () => {
    if (window.Notification && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, { once: true });
});
</script>"""

new_content = content[:start_idx] + new_script + content[end_idx:]
with codecs.open(path, 'w', 'utf-8') as f:
    f.write(new_content)
