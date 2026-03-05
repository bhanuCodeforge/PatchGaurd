import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true;
  }

  return router.createUrlTree(['/login']);
};

export const roleGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  
  const expectedRole = route.data['role'];
  
  if (!authService.isAuthenticated()) {
    return router.createUrlTree(['/login']);
  }
  
  if (expectedRole === 'admin' && !authService.isAdmin()) {
    return router.createUrlTree(['/dashboard']);
  }
  
  if (expectedRole === 'operator' && !authService.isOperatorOrAbove()) {
    return router.createUrlTree(['/dashboard']);
  }

  return true;
};
