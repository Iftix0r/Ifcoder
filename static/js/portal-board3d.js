/* Robot yo'li uchun 3D taxta. Faqat ko'rinish: kod va baholash serverda, bu fayl hodisalarni chizadi. */
import * as THREE from "/static/vendor/three/three.module.min.js";

// Yo'l yorqin, devor to'q va past: bola qayerdan yurishni bir qarashda ko'rsin
const WALL_COLORS = [0x23246b, 0x2a2b7a, 0x1e1f5e];

function roundedBox(width, height, depth, radius) {
  const x = -width / 2;
  const z = -depth / 2;
  const shape = new THREE.Shape();
  shape.moveTo(x + radius, z);
  shape.lineTo(x + width - radius, z);
  shape.quadraticCurveTo(x + width, z, x + width, z + radius);
  shape.lineTo(x + width, z + depth - radius);
  shape.quadraticCurveTo(x + width, z + depth, x + width - radius, z + depth);
  shape.lineTo(x + radius, z + depth);
  shape.quadraticCurveTo(x, z + depth, x, z + depth - radius);
  shape.lineTo(x, z + radius);
  shape.quadraticCurveTo(x, z, x + radius, z);
  const bevel = Math.min(radius * 0.5, 0.05);
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: height - bevel * 2,
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 3,
    curveSegments: 6,
  });
  geometry.rotateX(-Math.PI / 2);
  geometry.translate(0, bevel, 0);
  return geometry;
}

function glowTexture(color) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const context = canvas.getContext("2d");
  const gradient = context.createRadialGradient(64, 64, 0, 64, 64, 64);
  gradient.addColorStop(0, color);
  gradient.addColorStop(1, "rgba(0,0,0,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(canvas);
}

const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

function buildRobot(color) {
  const robot = new THREE.Group();
  const paint = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.28, roughness: 0.32, metalness: 0.2 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x151833, roughness: 0.6 });
  const eye = new THREE.MeshStandardMaterial({ color: 0x22d3ee, emissive: 0x22d3ee, emissiveIntensity: 2.4 });

  const body = new THREE.Mesh(roundedBox(0.46, 0.4, 0.42, 0.13), paint);
  body.position.y = 0.14;
  const head = new THREE.Mesh(roundedBox(0.4, 0.28, 0.36, 0.11), paint);
  head.position.y = 0.56;
  const visor = new THREE.Mesh(roundedBox(0.3, 0.14, 0.05, 0.02), dark);
  visor.position.set(0, 0.63, -0.175);
  const eyes = [-0.075, 0.075].map((x) => {
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(0.04, 16, 12), eye);
    mesh.position.set(x, 0.7, -0.2);
    return mesh;
  });
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, 0.14), dark);
  stem.position.y = 0.91;
  const tip = new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 12), eye);
  tip.position.y = 1;
  const wheels = [-0.27, 0.27].map((x) => {
    const mesh = new THREE.Mesh(roundedBox(0.1, 0.16, 0.42, 0.04), dark);
    mesh.position.set(x, 0.02, 0);
    return mesh;
  });
  robot.add(body, head, visor, ...eyes, stem, tip, ...wheels);
  robot.traverse((part) => {
    part.castShadow = true;
  });
  robot.userData = { paint, tip };
  return robot;
}

function supported() {
  try {
    return Boolean(document.createElement("canvas").getContext("webgl2"));
  } catch {
    return false;
  }
}

function create(container) {
  container.classList.add("is-3d");
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  container.replaceChildren(renderer.domElement);

  const camera = new THREE.PerspectiveCamera(30, 2, 0.1, 200);
  const crystalGlow = glowTexture("rgba(34,211,238,0.85)");
  const exitGlow = glowTexture("rgba(52,211,153,0.9)");
  const clock = new THREE.Clock();

  let scene = null;
  let world = null;
  let robot = null;
  let crystals = new Map();
  let portal = null;
  let bursts = [];
  let stepMs = 340;
  let move = null;
  let spin = null;
  let shake = 0;
  let party = 0;
  let heading = 0;

  const toWorld = (x, y) => [x - world.width / 2 + 0.5, y - world.height / 2 + 0.5];

  function fit() {
    if (!world) return;
    const width = container.clientWidth || 400;
    const ratio = Math.min(Math.max(((world.height + 2) / (world.width + 1)) * 0.82, 0.42), 0.86);
    const height = Math.min(Math.round(width * ratio), 470);
    renderer.setSize(width, height);
    camera.aspect = width / height;
    // Xarita kadrga to'liq sig'adigan masofa
    const halfFov = THREE.MathUtils.degToRad(camera.fov / 2);
    const needHeight = (world.height * 0.92 + 1.6) / (2 * Math.tan(halfFov));
    const needWidth = (world.width + 1.4) / (2 * Math.tan(halfFov) * camera.aspect);
    const distance = Math.max(needHeight, needWidth) + 1.5;
    camera.position.set(0, distance * 0.93, distance * 0.46);
    camera.lookAt(0, 0, 0.1);
    camera.updateProjectionMatrix();
  }

  function addCrystal(x, y) {
    const [wx, wz] = toWorld(x, y);
    const group = new THREE.Group();
    const gem = new THREE.Mesh(
      new THREE.OctahedronGeometry(0.2),
      new THREE.MeshStandardMaterial({ color: 0x06b6d4, emissive: 0x0891b2, emissiveIntensity: 0.9, roughness: 0.12, metalness: 0.3, flatShading: true }),
    );
    gem.scale.set(1.25, 1.8, 1.25);
    gem.castShadow = true;
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: crystalGlow, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    halo.scale.setScalar(1);
    group.add(gem, halo);
    group.position.set(wx, 0.5, wz);
    group.userData = { gem, phase: Math.random() * 6, taken: 0 };
    scene.add(group);
    crystals.set(`${x},${y}`, group);
  }

  function addExit(x, y) {
    const [wx, wz] = toWorld(x, y);
    portal = new THREE.Group();
    const material = new THREE.MeshStandardMaterial({ color: 0x10b981, emissive: 0x059669, emissiveIntensity: 1.2 });
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.33, 0.045, 12, 40), material);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 0.05;
    const beam = new THREE.Mesh(
      new THREE.CylinderGeometry(0.31, 0.31, 1.3, 32, 1, true),
      new THREE.MeshBasicMaterial({ color: 0x34d399, transparent: true, opacity: 0.16, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending }),
    );
    beam.position.y = 0.65;
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.85), new THREE.MeshStandardMaterial({ color: 0xe2e8f0 }));
    pole.position.y = 0.45;
    const flag = new THREE.Mesh(new THREE.ConeGeometry(0.13, 0.3, 3), material);
    flag.rotation.z = -Math.PI / 2;
    flag.scale.z = 0.25;
    flag.position.set(0.15, 0.76, 0);
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: exitGlow, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    halo.scale.setScalar(1.5);
    halo.position.y = 0.2;
    pole.castShadow = true;
    portal.add(ring, beam, pole, flag, halo);
    portal.position.set(wx, 0.02, wz);
    portal.userData = { ring };
    scene.add(portal);
  }

  function load(next) {
    world = next;
    scene = new THREE.Scene();
    crystals = new Map();
    bursts = [];
    portal = null;
    move = spin = null;
    shake = party = 0;

    scene.add(new THREE.HemisphereLight(0xc7d2fe, 0x1e1b4b, 1.25));
    const sun = new THREE.DirectionalLight(0xffffff, 2.5);
    const span = Math.max(world.width, world.height);
    sun.position.set(-span * 0.45, span * 1.1, span * 0.5);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024);
    sun.shadow.camera.left = sun.shadow.camera.bottom = -span;
    sun.shadow.camera.right = sun.shadow.camera.top = span;
    sun.shadow.bias = -0.0006;
    sun.shadow.radius = 4;
    scene.add(sun);
    const rim = new THREE.PointLight(0xa855f7, span * 2.2, span * 2.5);
    rim.position.set(span * 0.5, 2.2, -span * 0.4);
    scene.add(rim);

    const base = new THREE.Mesh(
      roundedBox(world.width + 0.5, 0.7, world.height + 0.5, 0.3),
      new THREE.MeshStandardMaterial({ color: 0x14163a, roughness: 0.85 }),
    );
    base.position.y = -0.74;
    base.receiveShadow = true;
    scene.add(base);

    const tile = roundedBox(0.94, 0.14, 0.94, 0.1);
    const floors = [0x8fb4ff, 0xa9c5ff].map((color) => new THREE.MeshStandardMaterial({ color, roughness: 0.55 }));
    const walls = WALL_COLORS.map((color) => new THREE.MeshStandardMaterial({ color, roughness: 0.42, metalness: 0.12 }));
    const cap = new THREE.MeshStandardMaterial({ color: 0x3b3da8, emissive: 0x4338ca, emissiveIntensity: 0.35, roughness: 0.4 });
    const block = roundedBox(0.92, 0.34, 0.92, 0.12);
    const lid = roundedBox(0.72, 0.05, 0.72, 0.1);
    const blocked = new Set(world.walls.map(([x, y]) => `${x},${y}`));

    for (let y = 0; y < world.height; y++) {
      for (let x = 0; x < world.width; x++) {
        const [wx, wz] = toWorld(x, y);
        if (blocked.has(`${x},${y}`)) {
          const seed = (x * 7 + y * 13) % 3;
          const mesh = new THREE.Mesh(block, walls[seed]);
          const lift = seed * 0.035;
          mesh.position.set(wx, -0.04 + lift, wz);
          mesh.castShadow = mesh.receiveShadow = true;
          const top = new THREE.Mesh(lid, cap);
          top.position.set(wx, 0.285 + lift, wz);
          scene.add(mesh, top);
        } else {
          const mesh = new THREE.Mesh(tile, floors[(x + y) % 2]);
          mesh.position.set(wx, -0.12, wz);
          mesh.receiveShadow = true;
          scene.add(mesh);
        }
      }
    }
    if (world.exit) addExit(...world.exit);
    for (const [x, y] of world.crystals) addCrystal(x, y);

    const skin = getComputedStyle(container).getPropertyValue("--skin").trim() || "#6366f1";
    robot = buildRobot(new THREE.Color(skin));
    robot.scale.setScalar(1.25);
    const [rx, rz] = toWorld(world.robot.x, world.robot.y);
    robot.position.set(rx, 0.03, rz);
    heading = -THREE.MathUtils.degToRad(world.robot.d * 90);
    robot.rotation.y = heading;
    scene.add(robot);
    fit();
  }

  function place(x, y) {
    const [wx, wz] = toWorld(x, y);
    move = { from: robot.position.clone(), to: new THREE.Vector3(wx, 0.03, wz), start: performance.now(), ms: stepMs };
  }

  function turn(degrees) {
    const target = -THREE.MathUtils.degToRad(degrees);
    spin = { from: heading, to: target, start: performance.now(), ms: stepMs };
    heading = target;
  }

  function burst(position, color, count = 26) {
    const points = new Float32Array(count * 3);
    const speeds = [];
    for (let i = 0; i < count; i++) {
      points.set([position.x, position.y, position.z], i * 3);
      speeds.push(new THREE.Vector3((Math.random() - 0.5) * 3.4, Math.random() * 3.6 + 0.8, (Math.random() - 0.5) * 3.4));
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(points, 3));
    const material = new THREE.PointsMaterial({ color, size: 0.09, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
    const cloud = new THREE.Points(geometry, material);
    scene.add(cloud);
    bursts.push({ cloud, speeds, life: 0.9 });
  }

  function take(x, y) {
    const crystal = crystals.get(`${x},${y}`);
    if (!crystal) return;
    crystal.userData.taken = performance.now();
    burst(crystal.position, 0x67e8f9);
  }

  function crash() {
    shake = 1;
    robot.userData.paint.emissive.set(0xef4444);
    robot.userData.paint.emissiveIntensity = 1.1;
    burst(robot.position.clone().setY(0.5), 0xfb7185, 18);
  }

  function cheer() {
    party = 1;
    burst(robot.position.clone().setY(0.9), 0xfde68a, 50);
  }

  function animate() {
    requestAnimationFrame(animate);
    if (!scene || document.hidden) return;
    const delta = Math.min(clock.getDelta(), 0.05);
    const now = performance.now();
    const time = now / 1000;

    if (move) {
      const part = Math.min((now - move.start) / move.ms, 1);
      robot.position.lerpVectors(move.from, move.to, ease(part));
      robot.position.y = 0.03 + Math.sin(part * Math.PI) * 0.09;
      if (part === 1) move = null;
    } else if (party > 0) {
      party = Math.max(party - delta * 0.45, 0);
      robot.position.y = 0.03 + Math.abs(Math.sin(time * 9)) * 0.28 * party;
      robot.rotation.y += delta * 7 * party;
    } else {
      robot.position.y = 0.03 + Math.sin(time * 2.4) * 0.012;
    }
    if (spin) {
      const part = Math.min((now - spin.start) / spin.ms, 1);
      robot.rotation.y = spin.from + (spin.to - spin.from) * ease(part);
      if (part === 1) spin = null;
    }
    robot.userData.tip.scale.setScalar(1 + Math.sin(time * 5) * 0.16);

    for (const [key, crystal] of crystals) {
      const { gem, phase, taken } = crystal.userData;
      gem.rotation.y += delta * 1.7;
      if (taken) {
        const part = (now - taken) / 360;
        crystal.position.y += delta * 3.4;
        crystal.scale.setScalar(Math.max(1 - part, 0.001));
        if (part >= 1) {
          scene.remove(crystal);
          crystals.delete(key);
        }
      } else {
        crystal.position.y = 0.5 + Math.sin(time * 2.2 + phase) * 0.07;
      }
    }
    if (portal) portal.userData.ring.scale.setScalar(1 + Math.sin(time * 3) * 0.07);

    bursts = bursts.filter((item) => {
      item.life -= delta;
      const positions = item.cloud.geometry.attributes.position;
      item.speeds.forEach((speed, index) => {
        speed.y -= delta * 7;
        positions.setXYZ(
          index,
          positions.getX(index) + speed.x * delta,
          positions.getY(index) + speed.y * delta,
          positions.getZ(index) + speed.z * delta,
        );
      });
      positions.needsUpdate = true;
      item.cloud.material.opacity = Math.max(item.life / 0.9, 0);
      if (item.life > 0) return true;
      scene.remove(item.cloud);
      item.cloud.geometry.dispose();
      item.cloud.material.dispose();
      return false;
    });

    const offset = shake > 0 ? Math.sin(time * 70) * 0.09 * shake : 0;
    shake = Math.max(shake - delta * 2.4, 0);
    scene.position.x = offset;
    renderer.render(scene, camera);
  }

  new ResizeObserver(fit).observe(container);
  animate();
  return { load, place, turn, take, crash, cheer, setStep: (ms) => (stepMs = ms) };
}

window.Board3D = { supported, create };
