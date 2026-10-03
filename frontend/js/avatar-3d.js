/* Sinaliza — avatar 3D (Three.js)
   MOCK: o "boneco" é feito só de formas geométricas primitivas (esfera, cilindro,
   cápsula) organizadas em hierarquia de juntas — sem modelagem nem rig profissional.
   Serve para validar o pipeline de animação antes de plugar um modelo modelado/
   rigado de verdade (glTF/.glb). Quando isso acontecer, troque só _buildPuppet()
   por um carregador de glTF (THREE.GLTFLoader) que exponha os mesmos nomes de
   junta usados aqui (rightShoulder, rightElbow, rightWrist, head...) — o resto
   deste arquivo (render loop, interpolação de keyframes) continua igual.
*/
const lerp = (a, b, progress) => a + (b - a) * progress;

function interpolateJointRotation(keyframes, elapsedMs) {
  if (elapsedMs <= keyframes[0].t) return keyframes[0];
  const last = keyframes[keyframes.length - 1];
  if (elapsedMs >= last.t) return last;

  for (let i = 0; i < keyframes.length - 1; i++) {
    const from = keyframes[i];
    const to = keyframes[i + 1];
    if (elapsedMs >= from.t && elapsedMs <= to.t) {
      const progress = (elapsedMs - from.t) / (to.t - from.t || 1);
      return {
        rx: lerp(from.rx, to.rx, progress),
        ry: lerp(from.ry, to.ry, progress),
        rz: lerp(from.rz, to.rz, progress)
      };
    }
  }
  return last;
}

const Avatar3D = {
  _scene: null,
  _camera: null,
  _renderer: null,
  _joints: {},
  _activeSign: null,

  init(container) {
    const width = container.clientWidth || 280;
    const height = container.clientHeight || 280;

    this._scene = new THREE.Scene();
    this._camera = new THREE.PerspectiveCamera(35, width / height, 0.1, 100);
    this._camera.position.set(0, 1.4, 4);
    this._camera.lookAt(0, 1.25, 0);

    this._renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this._renderer.setSize(width, height);
    container.appendChild(this._renderer.domElement);

    this._scene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const keyLight = new THREE.DirectionalLight(0xffffff, 0.6);
    keyLight.position.set(2, 4, 3);
    this._scene.add(keyLight);

    this._buildPuppet();
    window.addEventListener('resize', () => this._handleResize(container));
    this._renderLoop();
  },

  _buildPuppet() {
    const skin = new THREE.MeshStandardMaterial({ color: 0xffcf9e });
    const shirt = new THREE.MeshStandardMaterial({ color: 0x2563eb });

    const root = new THREE.Group();
    this._scene.add(root);

    const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.32, 0.55, 4, 8), shirt);
    torso.position.y = 1.0;
    root.add(torso);

    const head = new THREE.Mesh(new THREE.SphereGeometry(0.26, 16, 16), skin);
    head.position.y = 1.62;
    this._joints.head = head; // rotaciona a própria cabeça (não precisa de grupo pai)
    root.add(head);

    const buildArm = side => {
      const shoulder = new THREE.Group();
      shoulder.position.set(side * 0.38, 1.32, 0);

      const upperArm = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.45, 8), skin);
      upperArm.position.y = -0.225;
      shoulder.add(upperArm);

      const elbow = new THREE.Group();
      elbow.position.y = -0.45;
      shoulder.add(elbow);

      const forearm = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.065, 0.4, 8), skin);
      forearm.position.y = -0.2;
      elbow.add(forearm);

      const wrist = new THREE.Group();
      wrist.position.y = -0.4;
      elbow.add(wrist);

      const hand = new THREE.Mesh(new THREE.SphereGeometry(0.085, 12, 12), skin);
      wrist.add(hand);

      root.add(shoulder);
      return { shoulder, elbow, wrist };
    };

    const rightArm = buildArm(1);
    this._joints.rightShoulder = rightArm.shoulder;
    this._joints.rightElbow = rightArm.elbow;
    this._joints.rightWrist = rightArm.wrist;

    const leftArm = buildArm(-1);
    this._joints.leftShoulder = leftArm.shoulder;
    this._joints.leftElbow = leftArm.elbow;
    this._joints.leftWrist = leftArm.wrist;
  },

  // glossKey: chave do SIGN_DICTIONARY (ver sign-dictionary.js)
  play(glossKey, { onEnd } = {}) {
    const sign = SIGN_DICTIONARY[glossKey] || SIGN_DICTIONARY.DEFAULT;
    this._activeSign = { sign, startedAt: performance.now(), onEnd };
  },

  _renderLoop() {
    const tick = () => {
      if (this._activeSign) {
        const { sign, startedAt, onEnd } = this._activeSign;
        const elapsedMs = Math.min(performance.now() - startedAt, sign.durationMs);

        for (const [jointName, keyframes] of Object.entries(sign.keyframes)) {
          const joint = this._joints[jointName];
          if (!joint) continue;
          const { rx, ry, rz } = interpolateJointRotation(keyframes, elapsedMs);
          joint.rotation.set(rx, ry, rz);
        }

        if (elapsedMs >= sign.durationMs) {
          this._activeSign = null;
          onEnd?.();
        }
      }

      this._renderer.render(this._scene, this._camera);
      requestAnimationFrame(tick);
    };
    tick();
  },

  _handleResize(container) {
    const width = container.clientWidth;
    const height = container.clientHeight;
    if (!width || !height) return;
    this._camera.aspect = width / height;
    this._camera.updateProjectionMatrix();
    this._renderer.setSize(width, height);
  }
};
