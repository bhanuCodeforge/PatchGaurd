import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ApiService } from './api.service';
import { environment } from '../../../environments/environment';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('ApiService', () => {
    let service: ApiService;
    let httpMock: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [ApiService]
        });
        service = TestBed.inject(ApiService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpMock.verify();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should make a GET request', () => {
        const dummyData = [{ id: 1, name: 'Test' }];
        service.get('/test/').subscribe(res => {
            expect(res).toEqual(dummyData);
        });

        const req = httpMock.expectOne(`${environment.apiUrl}/test/`);
        expect(req.request.method).toBe('GET');
        req.flush(dummyData);
    });

    it('should make a POST request', () => {
        const dummyData = { id: 1, name: 'Test' };
        service.post('/test/', dummyData).subscribe(res => {
            expect(res).toEqual(dummyData);
        });

        const req = httpMock.expectOne(`${environment.apiUrl}/test/`);
        expect(req.request.method).toBe('POST');
        expect(req.request.body).toEqual(dummyData);
        req.flush(dummyData);
    });
});
