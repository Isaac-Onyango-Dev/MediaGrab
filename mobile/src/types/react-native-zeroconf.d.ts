declare module "react-native-zeroconf" {
    export interface ZeroconfService {
        name?: string;
        type?: string;
        addresses?: string[];
        host?: string;
        port?: number;
        txt?: Record<string, string>;
        fullName?: string;
    }

    export interface ZeroconfOptions {
        timeout?: number;
    }

    class ZeroConf {
        constructor();

        scan(
            type: string,
            protocol: string,
            domain: string
        ): Promise<void>;

        stop(): void;

        removeDeviceListeners(): void;

        on(event: string, handler: (service?: ZeroconfService) => void): void;

        off(event: string, handler: (service?: ZeroconfService) => void): void;
    }

    export default ZeroConf;
}
