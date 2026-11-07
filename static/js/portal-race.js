/* Kod poygasi: 3D sahna brauzerda, qaysi darvoza to'g'riligini esa faqat server biladi. */
import * as THREE from "/static/vendor/three/three.module.min.js";

const { $, config, sound } = window.Kit;
const stage = $("stage");
const LANES = 4;
const LANE_WIDTH = 2.3;
const GATE_START = -120;
const CAR_Z = 0;
const laneX = (index) => (index - (LANES - 1) / 2) * LANE_WIDTH;

function supported() {
  try {
    return Boolean(document.createElement("canvas").getContext("webgl2"));
  } catch {
    return false;
  }
}

function canvasTexture(width, height, paint) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  paint(canvas.getContext("2d"), width, height);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

function skyTexture() {
  return canvasTexture(1024, 512, (context, width, height) => {
    const sky = context.createLinearGradient(0, 0, 0, height);
    // Ufq ekranning 40% balandligida: quyosh yerning orqasida qolmasin
    sky.addColorStop(0, "#0b0524");
    sky.addColorStop(0.2, "#3b0f6b");
    sky.addColorStop(0.34, "#c02679");
    sky.addColorStop(0.42, "#fb923c");
    context.fillStyle = sky;
    context.fillRect(0, 0, width, height);
    context.fillStyle = "#fff";
    for (let i = 0; i < 160; i++) {
      context.globalAlpha = Math.random() * 0.8;
      context.fillRect(Math.random() * width, Math.random() * height * 0.26, 1.6, 1.6);
    }
    context.globalAlpha = 1;
    const cx = width / 2;
    const cy = height * 0.33;
    const sun = context.createLinearGradient(0, cy - 100, 0, cy + 100);
    sun.addColorStop(0, "#fde68a");
    sun.addColorStop(0.55, "#fb7185");
    sun.addColorStop(1, "#c026d3");
    context.fillStyle = sun;
    context.beginPath();
    context.arc(cx, cy, 100, 0, Math.PI * 2);
    context.fill();
    context.globalCompositeOperation = "destination-out";
    for (let i = 0; i < 6; i++) context.fillRect(cx - 110, cy + 6 + i * 15, 220, 2.5 + i * 1.2);
    context.globalCompositeOperation = "destination-over";
    context.fillStyle = sky;
    context.fillRect(0, 0, width, height);
  });
}

function gridTexture() {
  const texture = canvasTexture(256, 256, (context, width) => {
    context.fillStyle = "#12062b";
    context.fillRect(0, 0, width, width);
    context.strokeStyle = "#e879f9";
    context.lineWidth = 5;
    context.shadowColor = "#e879f9";
    context.shadowBlur = 12;
    context.strokeRect(0, 0, width, width);
  });
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(36, 60);
  return texture;
}

function roadTexture() {
  const texture = canvasTexture(512, 512, (context, width, height) => {
    context.fillStyle = "#1b1650";
    context.fillRect(0, 0, width, height);
    context.strokeStyle = "#a5b4fc";
    context.lineWidth = 7;
    context.setLineDash([74, 54]);
    for (let i = 1; i < LANES; i++) {
      const x = (width / LANES) * i;
      context.beginPath();
      context.moveTo(x, 0);
      context.lineTo(x, height);
      context.stroke();
    }
  });
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(1, 26);
  return texture;
}

function buildCar(color) {
  const car = new THREE.Group();
  const paint = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.55, roughness: 0.25, metalness: 0.25 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x0b1020, roughness: 0.2, metalness: 0.7 });
  const shape = new THREE.Shape();
  shape.moveTo(-1.15, 0);
  shape.lineTo(-1.12, 0.26);
  shape.quadraticCurveTo(-0.5, 0.3, -0.3, 0.56);
  shape.lineTo(0.5, 0.56);
  shape.quadraticCurveTo(0.8, 0.34, 1.2, 0.3);
  shape.lineTo(1.25, 0);
  shape.closePath();
  const body = new THREE.ExtrudeGeometry(shape, { depth: 1.1, bevelEnabled: true, bevelThickness: 0.07, bevelSize: 0.05, bevelSegments: 3 });
  body.translate(0, 0, -0.55);
  body.rotateY(Math.PI / 2);
  const shell = new THREE.Mesh(body, paint);
  shell.position.y = 0.2;
  const glass = new THREE.Mesh(new THREE.BoxGeometry(0.98, 0.2, 0.74), dark);
  glass.position.set(0, 0.68, -0.03);
  const tail = new THREE.Mesh(
    new THREE.BoxGeometry(1.08, 0.08, 0.05),
    new THREE.MeshBasicMaterial({ color: 0xff2d6f, toneMapped: false }),
  );
  tail.position.set(0, 0.42, 1.3);
  const stripe = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.03, 2.3), new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }));
  stripe.position.set(0, 0.79, 0);
  const wheels = [
    [-0.62, -0.72],
    [0.62, -0.72],
    [-0.62, 0.74],
    [0.62, 0.74],
  ].map(([x, z]) => {
    const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 0.2, 24), dark);
    wheel.rotation.z = Math.PI / 2;
    wheel.position.set(x, 0.25, z);
    return wheel;
  });
  const under = new THREE.PointLight(0x22d3ee, 8, 4);
  under.position.y = 0.12;
  car.add(shell, glass, tail, stripe, ...wheels, under);
  car.traverse((part) => {
    part.castShadow = true;
  });
  car.userData = { wheels };
  return car;
}

function gateMesh(text) {
  const texture = canvasTexture(256, 128, (context, width, height) => {
    context.fillStyle = "rgba(17, 12, 48, 0.9)";
    context.fillRect(0, 0, width, height);
    context.strokeStyle = "#f0abfc";
    context.lineWidth = 8;
    context.strokeRect(4, 4, width - 8, height - 8);
    context.fillStyle = "#fff";
    context.textAlign = "center";
    context.textBaseline = "middle";
    const size = text.length > 6 ? 40 : text.length > 3 ? 54 : 76;
    context.font = `800 ${size}px ui-monospace, monospace`;
    context.fillText(text, width / 2, height / 2 + 3, width - 22);
  });
  const group = new THREE.Group();
  const sign = new THREE.Mesh(new THREE.PlaneGeometry(2.1, 1.05), new THREE.MeshBasicMaterial({ map: texture, transparent: true, toneMapped: false, fog: false }));
  sign.position.y = 2.5;
  const material = new THREE.MeshStandardMaterial({ color: 0xf0abfc, emissive: 0xd946ef, emissiveIntensity: 2 });
  const posts = [-1.02, 1.02].map((x) => {
    const post = new THREE.Mesh(new THREE.BoxGeometry(0.08, 2, 0.08), material);
    post.position.set(x, 1, 0);
    return post;
  });
  group.add(sign, ...posts);
  group.userData = { material };
  return group;
}

function startGame() {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;
  stage.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = skyTexture();
  scene.fog = new THREE.Fog(0xb0266f, 55, 170);
  const camera = new THREE.PerspectiveCamera(62, 16 / 9, 0.1, 300);
  camera.position.set(0, 3.3, 7.4);
  camera.lookAt(0, 1.2, -12);

  scene.add(new THREE.HemisphereLight(0xf0abfc, 0x1e1b4b, 1.5));
  const sun = new THREE.DirectionalLight(0xffd7a8, 2.2);
  sun.position.set(-4, 9, -6);
  sun.castShadow = true;
  sun.shadow.camera.left = sun.shadow.camera.bottom = -8;
  sun.shadow.camera.right = sun.shadow.camera.top = 8;
  scene.add(sun);

  const grid = gridTexture();
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(240, 400), new THREE.MeshBasicMaterial({ map: grid }));
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(0, -0.02, -140);
  const road = roadTexture();
  const width = LANE_WIDTH * LANES;
  // Yoritilmaydigan material: quyosh yo'lni xira jigarrang qilib yubormasin
  const asphalt = new THREE.Mesh(new THREE.PlaneGeometry(width, 400), new THREE.MeshBasicMaterial({ map: road, toneMapped: false }));
  asphalt.rotation.x = -Math.PI / 2;
  asphalt.position.set(0, 0, -140);
  const rails = [-1, 1].map((side) => {
    const rail = new THREE.Mesh(
      new THREE.BoxGeometry(0.16, 0.16, 400),
      new THREE.MeshBasicMaterial({ color: 0x22d3ee, toneMapped: false }),
    );
    rail.position.set((side * width) / 2, 0.1, -140);
    return rail;
  });
  scene.add(ground, asphalt, ...rails);

  const hills = [];
  const hill = new THREE.MeshStandardMaterial({ color: 0x4c1d95, flatShading: true, roughness: 0.9 });
  for (let i = 0; i < 26; i++) {
    const side = i % 2 ? 1 : -1;
    const size = 7 + Math.random() * 13;
    const mesh = new THREE.Mesh(new THREE.ConeGeometry(size, size * (0.7 + Math.random() * 0.6), 5), hill);
    mesh.position.set(side * (17 + Math.random() * 34), size * 0.35, -i * 12);
    mesh.rotation.y = Math.random() * 6;
    scene.add(mesh);
    hills.push(mesh);
  }
  const lamps = [];
  const lampGlow = new THREE.MeshStandardMaterial({ color: 0xfbcfe8, emissive: 0xf472b6, emissiveIntensity: 3 });
  const lampPost = new THREE.MeshStandardMaterial({ color: 0x1e1b4b });
  for (let i = 0; i < 16; i++) {
    const side = i % 2 ? 1 : -1;
    const lamp = new THREE.Group();
    const post = new THREE.Mesh(new THREE.BoxGeometry(0.12, 3.6, 0.12), lampPost);
    post.position.y = 1.8;
    const bulb = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.12, 0.2), lampGlow);
    bulb.position.set(-side * 0.42, 3.55, 0);
    lamp.add(post, bulb);
    lamp.position.set(side * (width / 2 + 0.8), 0, -i * 12);
    scene.add(lamp);
    lamps.push(lamp);
  }

  const skin = getComputedStyle(stage).getPropertyValue("--skin").trim() || "#22d3ee";
  const car = buildCar(new THREE.Color(skin));
  car.position.set(laneX(1), 0, CAR_Z);
  scene.add(car);

  let phase = "ready"; // ready | driving | waiting | review | over
  let pace = 24;
  let answers = [];
  let lives = config.lives;
  let score = 0;
  let combo = 1;
  let lane = 1;
  let gates = [];
  let sparks = [];
  let speed = 16;
  let cruise = 16;
  let gateSpeed = 0;
  let boost = 0;
  let shake = 0;
  let last = performance.now();

  function resize() {
    const box = stage.getBoundingClientRect();
    renderer.setSize(box.width, box.height, false);
    camera.aspect = box.width / box.height;
    camera.updateProjectionMatrix();
  }

  function drawLives() {
    $("lives").setAttribute("aria-label", `${lives} ta jon`);
    $("lives").replaceChildren(
      ...Array.from({ length: config.lives }, (_, index) => {
        const heart = document.createElement("span");
        heart.className = index < lives ? "heart-on" : "heart-off";
        heart.append($("heart-template").content.cloneNode(true));
        return heart;
      }),
    );
  }

  function showHud() {
    $("score").textContent = score;
    $("combo").textContent = combo > 1 ? `×${combo}` : "";
    $("wave").textContent = `${Math.min(answers.length + 1, config.questions.length)}-darvoza / ${config.questions.length}`;
  }

  function markLane() {
    [...$("lanes").children].forEach((button, index) => button.classList.toggle("is-on", index === lane));
  }

  function aim(index) {
    if (phase !== "driving") return;
    lane = Math.max(0, Math.min(LANES - 1, index));
    markLane();
    sound.step();
  }

  function clearGates() {
    for (const gate of gates) scene.remove(gate);
    gates = [];
  }

  function startWave() {
    const question = config.questions[answers.length];
    $("race-code").innerHTML = question.code.split("\n").map(window.Kit.colorize).join("\n");
    $("race-why").hidden = true;
    clearGates();
    gates = question.options.map((text, index) => {
      const gate = gateMesh(text);
      gate.position.set(laneX(index), 0, GATE_START);
      scene.add(gate);
      return gate;
    });
    $("lanes").replaceChildren(
      ...question.options.map((text, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "race-lane";
        button.textContent = text;
        button.addEventListener("click", () => aim(index));
        return button;
      }),
    );
    // Kod qancha uzun bo'lsa, o'qishga shuncha ko'p vaqt
    const seconds = pace + question.code.split("\n").length * 2.5;
    gateSpeed = Math.abs(GATE_START) / seconds;
    cruise = gateSpeed;
    phase = "driving";
    markLane();
    showHud();
    stage.focus();
  }

  function restart() {
    answers = [];
    lives = config.lives;
    score = 0;
    combo = 1;
    drawLives();
    $("race-overlay").hidden = true;
    startWave();
  }

  function showReady() {
    clearGates();
    phase = "ready";
    $("race-why").hidden = true;
    $("race-overlay").hidden = false;
  }

  function spray(color, count = 44) {
    const material = new THREE.MeshBasicMaterial({ color });
    const piece = new THREE.BoxGeometry(0.12, 0.12, 0.12);
    for (let i = 0; i < count; i++) {
      const mesh = new THREE.Mesh(piece, material);
      mesh.position.set(car.position.x, 1.2, car.position.z - 1.6);
      mesh.userData = {
        velocity: new THREE.Vector3((Math.random() - 0.5) * 13, Math.random() * 9 + 2, (Math.random() - 0.5) * 11),
        life: 0.8,
      };
      scene.add(mesh);
      sparks.push(mesh);
    }
  }

  async function passGate() {
    phase = "waiting";
    const chosen = lane;
    const data = await window.Kit.post({ answers: [...answers, chosen] });
    if (data.failed) {
      phase = "review";
      $("why-text").textContent = data.message;
      $("race-next").textContent = "Davom";
      $("race-next").onclick = startWave;
      $("race-why").hidden = false;
      return;
    }
    answers.push(chosen);
    lives = data.lives;
    drawLives();
    const buttons = [...$("lanes").children];
    buttons[data.right].classList.add("is-right");
    if (data.correct) {
      score += 100 * combo;
      combo += 1;
      boost = 1;
      spray(0x34d399);
      sound.take();
    } else {
      combo = 1;
      shake = 1;
      buttons[chosen].classList.add("is-wrong");
      spray(0xfb7185, 26);
      sound.bad();
    }
    showHud();
    clearGates();
    $("why-text").textContent = `${data.correct ? "To'g'ri!" : "Xato."} ${data.why}`;
    $("race-why").hidden = false;
    if (data.finished) {
      window.Kit.saveProgress(data);
      phase = "over";
      $("race-next").textContent = data.ok ? "Natija" : "Qaytadan";
      $("race-next").onclick = data.ok
        ? () => {
            $("race-why").hidden = true;
            window.Kit.win(data, `${score} ball.`, showReady);
          }
        : restart;
    } else {
      phase = "review";
      $("race-next").textContent = "Davom";
      $("race-next").onclick = startWave;
    }
    $("race-next").focus();
  }

  function frame(now) {
    requestAnimationFrame(frame);
    const delta = Math.min((now - last) / 1000, 0.05);
    last = now;
    if (document.hidden) return;

    speed += (cruise * (1 + boost * 1.6) - speed) * Math.min(delta * 3, 1);
    boost = Math.max(boost - delta * 0.8, 0);
    const distance = speed * delta;
    road.offset.y += distance / 15;
    grid.offset.y += distance / 6.6;

    for (const list of [hills, lamps]) {
      for (const item of list) {
        item.position.z += distance;
        if (item.position.z > 14) item.position.z -= list === hills ? 312 : 192;
      }
    }

    if (phase === "driving") {
      for (const gate of gates) {
        gate.position.z += gateSpeed * delta;
        gate.userData.material.emissiveIntensity = 2 + Math.sin(now / 120) * 0.8;
      }
      if (gates[0]?.position.z >= CAR_Z - 1.2) passGate();
    }

    const targetX = laneX(lane);
    const drift = targetX - car.position.x;
    car.position.x += drift * Math.min(delta * 9, 1);
    car.rotation.y = -drift * 0.13;
    car.rotation.z = -drift * 0.07;
    car.position.y = Math.sin(now / 170) * 0.02;
    for (const wheel of car.userData.wheels) wheel.rotation.x += speed * delta;

    sparks = sparks.filter((spark) => {
      spark.userData.life -= delta;
      spark.userData.velocity.y -= delta * 20;
      spark.position.addScaledVector(spark.userData.velocity, delta);
      spark.rotation.x += delta * 9;
      if (spark.userData.life > 0) return true;
      scene.remove(spark);
      return false;
    });

    camera.fov += (62 + boost * 18 - camera.fov) * Math.min(delta * 6, 1);
    camera.position.x += (car.position.x * 0.45 - camera.position.x) * Math.min(delta * 5, 1);
    camera.position.y = 3.3 + (shake > 0 ? Math.sin(now / 16) * 0.2 * shake : 0);
    shake = Math.max(shake - delta * 2, 0);
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
  }

  document.querySelectorAll("[data-pace]").forEach((button) => {
    const choose = () => {
      pace = Number(button.dataset.pace);
      document.querySelectorAll("[data-pace]").forEach((item) => item.classList.toggle("is-active", item === button));
    };
    button.addEventListener("click", choose);
    if (Number(button.dataset.pace) === pace) choose();
  });
  $("race-start").addEventListener("click", restart);
  renderer.domElement.addEventListener("pointerdown", (event) => {
    const box = renderer.domElement.getBoundingClientRect();
    const side = (event.clientX - box.left) / box.width;
    aim(side < 0.5 ? lane - 1 : lane + 1);
  });
  addEventListener("keydown", (event) => {
    if (phase !== "driving") return;
    if (event.key === "ArrowLeft") aim(lane - 1);
    else if (event.key === "ArrowRight") aim(lane + 1);
    else if ("1234".includes(event.key)) aim(Number(event.key) - 1);
    else return;
    event.preventDefault();
  });
  new ResizeObserver(resize).observe(stage);

  resize();
  drawLives();
  showHud();
  requestAnimationFrame(frame);
}

if (supported()) {
  startGame();
} else {
  $("overlay-title").textContent = "Bu qurilmada 3D ishlamayapti";
  $("overlay-text").textContent = "Brauzeringiz 3D grafikani qo'llamaydi. Kod kosmosi o'yini xuddi shu bilimni o'rgatadi.";
  $("race-start").hidden = true;
  document.querySelector("#race-overlay .segmented").hidden = true;
}
