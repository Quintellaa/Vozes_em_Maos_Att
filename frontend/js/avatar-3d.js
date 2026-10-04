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
        rx: lerp(from.rx || 0, to.rx || 0, progress),
        ry: lerp(from.ry || 0, to.ry || 0, progress),
        rz: lerp(from.rz || 0, to.rz || 0, progress)
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
    this._camera.position.set(0, 1.35, 3.2);
    this._camera.lookAt(0, 1.25, 0);

    this._renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this._renderer.setSize(width, height);
    container.appendChild(this._renderer.domElement);

    this._scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const keyLight = new THREE.DirectionalLight(0xffffff, 0.75);
    keyLight.position.set(2, 4, 3);
    this._scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0xbfdbfe, 0.35); // azulado suave, do lado oposto
    fillLight.position.set(-3, 1, 2);
    this._scene.add(fillLight);

    this._buildPuppet();
    window.addEventListener('resize', () => this._handleResize(container));
    this._renderLoop();
  },

  _buildPuppet() {
    // roughness/metalness baixos dão um acabamento mais "fosco de brinquedo",
    // em vez do plástico brilhante que o MeshStandardMaterial tem por padrão.
    const skin = new THREE.MeshStandardMaterial({ color: 0xffcf9e, roughness: 0.55, metalness: 0.04 });
    const shirt = new THREE.MeshStandardMaterial({ color: 0x2563eb, roughness: 0.5, metalness: 0.04 });
    const hair = new THREE.MeshStandardMaterial({ color: 0xa8571f, roughness: 0.6, metalness: 0.02 });
    const face = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.3 });
    const cuff = new THREE.MeshStandardMaterial({ color: 0x1d4ed8, roughness: 0.5 });

    const root = new THREE.Group();
    this._scene.add(root);

    // Tronco menor e mais baixo — com os valores antigos, o topo arredondado da
    // cápsula ficava em y=1.54, invadindo a cabeça (que começa em y=1.2).
    const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.3, 0.28, 4, 12), shirt);
    torso.position.y = 0.82;
    root.add(torso);

    // Pescoço — preenche o intervalo entre o topo do tronco (y≈1.26) e a base da cabeça (y≈1.2).
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.12, 0.14, 12), skin);
    neck.position.y = 1.22;
    root.add(neck);

    // Cabeça é um Group (não só uma esfera) porque carrega olhos/boca/cabelo junto —
    // assim, quando a glosa anima a junta "head", o rosto inteiro gira com ela.
    const headGroup = new THREE.Group();
    headGroup.position.y = 1.5;
    root.add(headGroup);
    this._joints.head = headGroup;

    const skull = new THREE.Mesh(new THREE.SphereGeometry(0.3, 24, 24), skin);
    headGroup.add(skull);

    const eyeGeometry = new THREE.SphereGeometry(0.035, 10, 10);
    const leftEye = new THREE.Mesh(eyeGeometry, face);
    leftEye.position.set(-0.1, 0.03, 0.285);
    headGroup.add(leftEye);
    const rightEye = new THREE.Mesh(eyeGeometry, face);
    rightEye.position.set(0.1, 0.03, 0.285);
    headGroup.add(rightEye);

    // Metade de um torus = um arco; girado 180°, o arco abre pra cima (sorriso).
    const mouth = new THREE.Mesh(new THREE.TorusGeometry(0.06, 0.015, 8, 16, Math.PI), face);
    mouth.position.set(0, -0.08, 0.285);
    mouth.rotation.z = Math.PI;
    headGroup.add(mouth);

    // "Touca" de cabelo: topo de uma esfera levemente maior que a cabeça.
    // Os 2 últimos parâmetros (thetaStart, thetaLength) controlam o corte VERTICAL
    // (de 0 = polo do topo, até π = polo de baixo) — por isso 0.38π ≈ 68°, só o
    // suficiente pra cobrir o alto da cabeça sem descer até a altura dos olhos.
    const hairCap = new THREE.Mesh(
      new THREE.SphereGeometry(0.315, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.38),
      hair
    );
    hairCap.position.y = 0.04;
    headGroup.add(hairCap);

    // Palma + 4 dedos + polegar. Ainda estáticos (não dobram individualmente) —
    // o próximo passo é dar a cada dedo sua própria junta para variar a
    // configuração de mão por sinal, que é um parâmetro essencial em Libras.
    const buildHand = () => {
      const handGroup = new THREE.Group();

      const palm = new THREE.Mesh(new THREE.SphereGeometry(0.075, 14, 14), skin);
      palm.scale.set(1, 0.8, 0.55); // achata a esfera para parecer uma palma, não uma bola
      handGroup.add(palm);

      // 4 dedos (indicador → mindinho), espalhados em X, saindo da base da palma.
      const fingerXOffsets = [-0.045, -0.015, 0.015, 0.045];
      const fingerLengths = [0.07, 0.085, 0.08, 0.065]; // médio é o mais longo
      fingerXOffsets.forEach((x, i) => {
        const length = fingerLengths[i];
        const finger = new THREE.Mesh(new THREE.CapsuleGeometry(0.012, length, 3, 6), skin);
        finger.position.set(x, -0.06 - length / 2, 0.015);
        handGroup.add(finger);
      });

      // Polegar: mais curto, deslocado pro lado e girado, pra sugerir oponibilidade.
      const thumb = new THREE.Mesh(new THREE.CapsuleGeometry(0.014, 0.05, 3, 6), skin);
      thumb.position.set(0.07, -0.015, 0.035);
      thumb.rotation.z = Math.PI / 5;
      handGroup.add(thumb);

      return handGroup;
    };

    const buildArm = side => {
      const shoulder = new THREE.Group();
      // O tronco (CapsuleGeometry raio 0.3) se projeta até z=0.3 no ponto mais à
      // frente. z=0.4 aqui garante uma folga de verdade além disso — como a
      // rotação do ombro/cotovelo/pulso é só em Z, essa profundidade não muda
      // durante a animação, então o braço fica sempre à frente do corpo,
      // qualquer que seja o ângulo.
      shoulder.position.set(side * 0.4, 1.0, 0.4);

      const upperArm = new THREE.Mesh(new THREE.CapsuleGeometry(0.075, 0.18, 4, 8), skin);
      upperArm.position.y = -0.12;
      shoulder.add(upperArm);

      const elbow = new THREE.Group();
      elbow.position.y = -0.24;
      shoulder.add(elbow);

      const forearm = new THREE.Mesh(new THREE.CapsuleGeometry(0.065, 0.16, 4, 8), skin);
      forearm.position.y = -0.1;
      elbow.add(forearm);

      const wrist = new THREE.Group();
      wrist.position.y = -0.2;
      elbow.add(wrist);

      // Pulseira de cor contrastante só pra marcar visualmente onde o pulso dobra.
      const wristCuff = new THREE.Mesh(new THREE.TorusGeometry(0.075, 0.02, 8, 16), cuff);
      wristCuff.rotation.x = Math.PI / 2;
      wristCuff.position.y = 0.04;
      wrist.add(wristCuff);

      // Mão deslocada um pouco abaixo do pulso para não ficar escondida atrás do antebraço.
      const hand = buildHand();
      hand.position.y = -0.03;
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

  // animation: { durationMs, keyframes: { nomeDaJunta: [{t, rz}, ...] } }
  // vinda de sign-animations.js (movimentos reais do dataset).
  play(animation, { onEnd } = {}) {
    this._activeSign = { sign: animation, startedAt: performance.now(), onEnd };
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
          joint.rotation.set(rx || 0, ry || 0, rz || 0);
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
