import { useState, useEffect, useRef } from 'react';
import { Text, View, Button, Platform, StyleSheet, Alert } from 'react-native';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants'; // Tambahan modul pembaca ID

// Konfigurasi bagaimana notifikasi muncul saat aplikasi sedang dibuka
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export default function App() {
  const [expoPushToken, setExpoPushToken] = useState('');
  const notificationListener = useRef();
  const responseListener = useRef();

  // Baca konfigurasi dari app.json — edit di satu tempat aja biar gampang
  const { backendUrl, userId } = Constants.expoConfig?.extra || {};
  const BACKEND_URL = `${backendUrl || 'http://192.168.1.11:8000'}/register-device`;

  useEffect(() => {
    registerForPushNotificationsAsync().then(token => {
      if (token) {
        setExpoPushToken(token);
        sendTokenToBackend(token);
      }
    });

    notificationListener.current = Notifications.addNotificationReceivedListener(notification => {
      console.log('Notifikasi masuk:', notification);
    });

    responseListener.current = Notifications.addNotificationResponseReceivedListener(response => {
      console.log('Notifikasi diklik:', response);
    });

    return () => {
      Notifications.removeNotificationSubscription(notificationListener.current);
      Notifications.removeNotificationSubscription(responseListener.current);
    };
  }, []);

  const sendTokenToBackend = async (token) => {
    try {
      const response = await fetch(BACKEND_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId || 'dinar_01',
          token: token
        }),
      });
      const data = await response.json();
      console.log('Respon Backend:', data);
    } catch (error) {
      console.error('Gagal mengirim token ke backend:', error);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>CLI Notifier App</Text>
      <View style={styles.tokenContainer}>
        <Text style={styles.boldText}>Device Token Anda:</Text>
        <Text selectable style={styles.tokenText}>
          {expoPushToken || 'Meminta izin notifikasi...'}
        </Text>
      </View>
      <Button
        title="Kirim Ulang Token ke Server"
        onPress={() => sendTokenToBackend(expoPushToken)}
        disabled={!expoPushToken}
      />
    </View>
  );
}

async function registerForPushNotificationsAsync() {
  let token;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#FF231F7C',
    });
  }

  if (Device.isDevice) {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;
    
    // Jika belum ada izin, munculkan pop-up permintaan
    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    
    if (finalStatus !== 'granted') {
      alert('Aplikasi butuh izin notifikasi agar bisa bekerja!');
      return;
    }
    
    // Tarik token asli dari server Expo menggunakan Project ID
    try {
      const projectId = Constants.expoConfig?.extra?.eas?.projectId;
      
      if (!projectId) {
        alert('Project ID belum terbaca! Pastikan sudah menjalankan npx eas-cli init di terminal.');
        return;
      }

      token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
    } catch (e) {
      console.log("Error mengambil token:", e);
      alert(`Gagal mengambil token: ${e.message}`);
    }
  } else {
    alert('Push Notifications hanya berfungsi di perangkat fisik, bukan simulator.');
  }

  return token;
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 20, backgroundColor: '#fff' },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 30 },
  tokenContainer: { alignItems: 'center', justifyContent: 'center', marginBottom: 30, padding: 15, backgroundColor: '#f0f0f0', borderRadius: 10 },
  boldText: { fontWeight: 'bold', fontSize: 16 },
  tokenText: { marginTop: 10, textAlign: 'center', color: '#555', fontSize: 12 }
});