import { TestBed } from '@angular/core/testing';
import { PatchService } from './patch.service';
import { ApiService } from './api.service';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('PatchService', () => {
    let service: PatchService;
    let apiMock: any;

    beforeEach(() => {
        apiMock = {
            get: vi.fn(),
            post: vi.fn()
        };
        TestBed.configureTestingModule({
            providers: [
                PatchService,
                { provide: ApiService, useValue: apiMock }
            ]
        });
        service = TestBed.inject(PatchService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should fetch patches', () => {
        const dummyRes = { results: [], count: 0 };
        apiMock.get.mockReturnValue(of(dummyRes));

        service.getPatches().subscribe(res => {
            expect(res).toEqual(dummyRes);
        });
        expect(apiMock.get).toHaveBeenCalledWith('/patches/', {});
    });

    it('should approve a patch', () => {
        const dummyRes = { status: 'success' };
        apiMock.post.mockReturnValue(of(dummyRes));

        service.approvePatch('1').subscribe(res => {
            expect(res).toEqual(dummyRes);
        });
        expect(apiMock.post).toHaveBeenCalledWith('/patches/1/approve/', { reason: '' });
    });

    it('should fetch patch stats', () => {
        const dummyRes = { total: 10 };
        apiMock.get.mockReturnValue(of(dummyRes));

        service.getStats().subscribe(res => {
            expect(res).toEqual(dummyRes);
        });
        expect(apiMock.get).toHaveBeenCalledWith('/patches/stats/');
    });
});
