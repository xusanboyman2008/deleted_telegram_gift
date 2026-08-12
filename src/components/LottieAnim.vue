<template>
  <div ref="container" class="lottie-container"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';

const props = defineProps({
  filename: {
    type: String,
    required: true
  },
  loop: {
    type: Boolean,
    default: true
  },
  autoplay: {
    type: Boolean,
    default: true
  }
});

const container = ref(null);
let anim = null;

const loadAnim = () => {
  if (!container.value || !window.lottie) return;
  if (anim) {
    anim.destroy();
    anim = null;
  }

  let animPath = props.filename;
  if (!animPath.startsWith('/') && !animPath.startsWith('http')) {
    animPath = `/animations/${animPath}`;
  }

  anim = window.lottie.loadAnimation({
    container: container.value,
    renderer: 'svg',
    loop: props.loop,
    autoplay: props.autoplay,
    path: animPath
  });
};

onMounted(() => {
  loadAnim();
});

watch(() => props.filename, () => {
  loadAnim();
});

onBeforeUnmount(() => {
  if (anim) {
    anim.destroy();
    anim = null;
  }
});
</script>

<style scoped>
.lottie-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
