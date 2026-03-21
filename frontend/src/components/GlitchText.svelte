<script lang="ts">
  import { cn } from '$lib/utils.js';

  let {
    text,
    speed = 1,
    enableShadows = true,
    enableOnHover = false,
    class: className = '',
  }: {
    text: string;
    speed?: number;
    enableShadows?: boolean;
    enableOnHover?: boolean;
    class?: string;
  } = $props();
</script>

<span
  data-text={text}
  style:--after-duration="{speed * 3}s"
  style:--before-duration="{speed * 2}s"
  style:--after-shadow={enableShadows ? '-5px 0 red' : 'none'}
  style:--before-shadow={enableShadows ? '5px 0 cyan' : 'none'}
  class={cn('glitch-text', enableOnHover && 'glitch-text--hover', className)}
>
  {text}
</span>

<style>
  .glitch-text {
    position: relative;
    display: inline-block;
    user-select: none;
    color: var(--color-card-foreground);
  }

  .glitch-text::after,
  .glitch-text::before {
    content: attr(data-text);
    position: absolute;
    top: 0;
    overflow: hidden;
    clip-path: inset(0 0 0 0);
    color: var(--color-card-foreground);
    background: var(--color-card);
  }

  .glitch-text::after {
    left: 10px;
    text-shadow: var(--after-shadow);
    animation: glitch var(--after-duration, 1.5s) infinite linear alternate-reverse;
  }

  .glitch-text::before {
    left: -10px;
    text-shadow: var(--before-shadow);
    animation: glitch var(--before-duration, 1s) infinite linear alternate-reverse;
  }

  .glitch-text--hover {
    cursor: pointer;
  }

  .glitch-text--hover::after,
  .glitch-text--hover::before {
    content: '';
    opacity: 0;
  }

  .glitch-text--hover:hover::after,
  .glitch-text--hover:hover::before {
    content: attr(data-text);
    opacity: 1;
  }

  .glitch-text--hover:hover::after {
    text-shadow: var(--after-shadow);
    animation: glitch var(--after-duration, 1.5s) infinite linear alternate-reverse;
  }

  .glitch-text--hover:hover::before {
    text-shadow: var(--before-shadow);
    animation: glitch var(--before-duration, 1s) infinite linear alternate-reverse;
  }

  @keyframes glitch {
    0% {
      clip-path: inset(20% 0 50% 0);
    }
    5% {
      clip-path: inset(10% 0 60% 0);
    }
    10% {
      clip-path: inset(15% 0 55% 0);
    }
    15% {
      clip-path: inset(25% 0 35% 0);
    }
    20% {
      clip-path: inset(30% 0 40% 0);
    }
    25% {
      clip-path: inset(40% 0 20% 0);
    }
    30% {
      clip-path: inset(10% 0 60% 0);
    }
    35% {
      clip-path: inset(15% 0 55% 0);
    }
    40% {
      clip-path: inset(25% 0 35% 0);
    }
    45% {
      clip-path: inset(30% 0 40% 0);
    }
    50% {
      clip-path: inset(20% 0 50% 0);
    }
    55% {
      clip-path: inset(10% 0 60% 0);
    }
    60% {
      clip-path: inset(15% 0 55% 0);
    }
    65% {
      clip-path: inset(25% 0 35% 0);
    }
    70% {
      clip-path: inset(30% 0 40% 0);
    }
    75% {
      clip-path: inset(40% 0 20% 0);
    }
    80% {
      clip-path: inset(20% 0 50% 0);
    }
    85% {
      clip-path: inset(10% 0 60% 0);
    }
    90% {
      clip-path: inset(15% 0 55% 0);
    }
    95% {
      clip-path: inset(25% 0 35% 0);
    }
    100% {
      clip-path: inset(30% 0 40% 0);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .glitch-text::after,
    .glitch-text::before,
    .glitch-text--hover::after,
    .glitch-text--hover::before,
    .glitch-text--hover:hover::after,
    .glitch-text--hover:hover::before {
      content: none;
      animation: none;
    }
  }
</style>
