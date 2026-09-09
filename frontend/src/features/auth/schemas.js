import { z } from 'zod';

export const signInSchema = z.object({
  email: z
    .string()
    .min(1, { message: 'Email address is required' })
    .email({ message: 'Please enter a valid email address' }),
  password: z
    .string()
    .min(1, { message: 'Password is required' }),
});

export const signUpSchema = z.object({
  full_name: z
    .string()
    .min(2, { message: 'Full name must be at least 2 characters' }),
  email: z
    .string()
    .min(1, { message: 'Email address is required' })
    .email({ message: 'Please enter a valid email address' }),
  username: z
    .string()
    .min(3, { message: 'Username must be at least 3 characters' })
    .regex(/^[a-zA-Z0-9_]+$/, { message: 'Username may only contain letters, numbers, and underscores' }),
  password: z
    .string()
    .min(6, { message: 'Password must be at least 6 characters' }),
  role: z.string().default('admin'),
});

export const forgotPasswordSchema = z.object({
  email: z
    .string()
    .min(1, { message: 'Email address is required' })
    .email({ message: 'Please enter a valid email address' }),
});

export const resetPasswordSchema = z.object({
  password: z
    .string()
    .min(6, { message: 'Password must be at least 6 characters' }),
  confirm_password: z
    .string()
    .min(1, { message: 'Please confirm your password' }),
}).refine((data) => data.password === data.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
});

export const organizationSettingsSchema = z.object({
  name: z.string().min(2, { message: 'Organization name is required' }),
  primary_counter_name: z.string().min(1, { message: 'Primary counter name is required' }),
  fefo_alerts_enabled: z.boolean().default(true),
  plan_type: z.enum(['single_pharmacy', 'multi_branch']).default('single_pharmacy'),
});
