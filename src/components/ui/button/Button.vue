<script setup lang="ts">
import { Primitive, type PrimitiveProps } from 'reka-ui'
import { cva } from 'class-variance-authority'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
interface Props extends PrimitiveProps { variant?: 'default' | 'outline'; class?: ClassValue }
const props = withDefaults(defineProps<Props>(), { as: 'button', variant: 'default' })
const variants = cva('button', { variants: { variant: { default: 'button-primary', outline: 'button-outline' } } })
</script>
<template><Primitive :as="props.as" :as-child="props.asChild" :class="twMerge(clsx(variants({ variant }), props.class))"><slot /></Primitive></template>
