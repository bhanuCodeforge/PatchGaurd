import { TestBed } from '@angular/core/testing';
import { DeviceService } from './device.service';
import { ApiService } from './api.service';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('DeviceService', () => {
    let service: DeviceService;
    let apiMock: any;

    beforeEach(() => {
        apiMock = {
            get: vi.fn(),
            post: vi.fn(),
            patch: vi.fn(),
            delete: vi.fn()
        };
        TestBed.configureTestingModule({
            providers: [
                DeviceService,
                { provide: ApiService, useValue: apiMock }
            ]
        });
        service = TestBed.inject(DeviceService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should fetch devices', () => {
        const dummyRes = { results: [], count: 0 };
        apiMock.get.mockReturnValue(of(dummyRes));

        service.getDevices().subscribe(res => {
            expect(res).toEqual(dummyRes);
        });
        expect(apiMock.get).toHaveBeenCalledWith('/devices/', {});
    });

    it('should fetch a single device', () => {
        const dummyDevice = { id: '1', hostname: 'test' };
        apiMock.get.mockReturnValue(of(dummyDevice));

        service.getDeviceById('1').subscribe(res => {
            expect(res).toEqual(dummyDevice);
        });
        expect(apiMock.get).toHaveBeenCalledWith('/devices/1/');
    });

    it('should create a device', () => {
        const dummyDevice = { hostname: 'new' };
        apiMock.post.mockReturnValue(of(dummyDevice));

        service.createDevice(dummyDevice).subscribe(res => {
            expect(res).toEqual(dummyDevice);
        });
        expect(apiMock.post).toHaveBeenCalledWith('/devices/', dummyDevice);
    });

    it('should update a device', () => {
        const dummyUpdate = { description: 'test' };
        apiMock.patch.mockReturnValue(of(dummyUpdate));

        service.updateDevice('1', dummyUpdate).subscribe(res => {
            expect(res).toEqual(dummyUpdate);
        });
        expect(apiMock.patch).toHaveBeenCalledWith('/devices/1/', dummyUpdate);
    });

    it('should delete a device', () => {
        apiMock.delete.mockReturnValue(of(null));

        service.deleteDevice('1').subscribe(res => {
            expect(res).toBeNull();
        });
        expect(apiMock.delete).toHaveBeenCalledWith('/devices/1/');
    });
});
