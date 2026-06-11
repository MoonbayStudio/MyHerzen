const play = document.querySelector('.playimg'),
      gplay = document.querySelector('.giant__play'),
      p = document.querySelector('.o'),
      pclose = document.querySelector('.pclosea'),
      pplay = document.querySelector('.pplay'),
      asoarg =  document.getElementById('asoarg'), 
      tunnel = document.getElementById('tunnel'),
      tm = document.querySelector('.tm'),
      album = document.querySelector('.album'),
      pbar = document.querySelector('.pbar'),
      popbar = document.querySelector('popup__bar'),
      show = document.querySelector('.show'),
      giant = document.getElementById('giant'),
      gc = document.querySelector('.giant__container'),
      tplay = document.querySelector('.tunnel__playbtn'),
      tbc = document.querySelector('.tunnel__bar__container1'),
      tb = document.querySelector('.tunnel__bar'),
      tba = document.querySelector('.tunnel__bar::after')
var count = 0
function change() {
  gplay.src = "images/pause1.png"
  pplay.src = "images/pause2.png"
}
function change2() {
  gplay.src = "images/play1.png"
  play.src = "images/play1.png"
  pplay.src = "images/play2.png"
}
function Loadgsong() {
  asoarg.src = 'sounds/asoarg.mp3'
}
function Playgsong() {
  album.classList.add('playing'),
  Loadgsong(),
  asoarg.play(),
  p.classList.remove('hidediv'),
  p.classList.add('popup'),
  change(),
  giant.classList.replace('giant', 'giantplay'),
  album.classList.add('hidediv'),
  gc.classList.remove('hidediv')
}
function Pausegsong() {
  album.classList.remove('playing'),
  asoarg.pause(),
  change2()
}
play.addEventListener('click', function() {
    if (album.classList.contains('playing')) {
      Pausegsong()
    }
    else {
      Playgsong()
    }
})
gplay.addEventListener('click', function() {
  isPlaying = album.classList.contains('playing')
    if (isPlaying) {
      Pausegsong()
    }
    else {
      Playgsong()
    }
})
pclose.addEventListener('click', function() {
  p.classList.replace('popup', 'hidepp')
})
pplay.addEventListener('click', function() {
  isPlaying = album.classList.contains('playing')
  if (isPlaying) {
    Pausegsong()
  }
  else {
    Playgsong()
  }
})
tm.addEventListener('timeupdate', function() {
  const progressp = (tm.currentTime / tm.duration) * 100
  tb.style.width = `${progressp}%`
  
})
tplay.addEventListener('click', function() {
  if (tunnel.classList.contains('playing')) {
    tunnel.classList.remove('playing')
    tplay.src = "images/play1.png"
    tm.pause()
  }
   else {
    tunnel.classList.add('played')    
    tunnel.classList.add('playing')
    tm.src = 'sounds/tunnel.mp3'
    tm.play()
    tplay.src = "images/pause1.png"
  }
})
tba.addEventListener('mousemove', function(e) {
  var x = e.clientX
  tb.style.width = `${x}%`
})